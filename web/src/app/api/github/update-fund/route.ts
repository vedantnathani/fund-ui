/**
 * POST /api/github/update-fund
 *
 * Server-side Route Handler. Reads GH_PAT from env (never exposed to client)
 * and commits changes to config/funds.json via GitHub Contents API.
 *
 * Request body:
 *   { action: 'add' | 'disable' | 'enable', fund: FundConfig | { id: string } }
 *
 * Responses:
 *   200 { success: true, sha: string }
 *   400 { error: string }   — validation failure
 *   401 { error: string }   — GH_PAT not configured
 *   500 { error: string }   — GitHub API error
 */

import { NextRequest, NextResponse } from 'next/server';
import { FundConfig } from '@/types';

const GITHUB_API = 'https://api.github.com';

function validateFundConfig(fund: FundConfig): string | null {
  if (!fund.id || !/^[a-z0-9-]+$/.test(fund.id)) {
    return "Field 'id' must be lowercase kebab-case (e.g. mirae-flexicap)";
  }
  if (!fund.name?.trim()) return "Field 'name' is required";
  if (!fund.amc?.trim()) return "Field 'amc' is required";
  if (!['equity', 'debt', 'hybrid', 'liquid'].includes(fund.type)) {
    return "Field 'type' must be one of: equity, debt, hybrid, liquid";
  }
  if (!fund.source_page?.startsWith('https://')) {
    return "Field 'source_page' must be a valid HTTPS URL";
  }
  if (!Array.isArray(fund.parser_preference) || fund.parser_preference.length === 0) {
    return "Field 'parser_preference' must have at least one entry";
  }
  const validParsers = ['excel', 'pdf_text', 'ocr'];
  for (const p of fund.parser_preference) {
    if (!validParsers.includes(p)) {
      return `Unknown parser '${p}'. Valid: ${validParsers.join(', ')}`;
    }
  }
  if (
    fund.significant_change_pp !== undefined &&
    (fund.significant_change_pp < 0.1 || fund.significant_change_pp > 5.0)
  ) {
    return "Field 'significant_change_pp' must be between 0.1 and 5.0";
  }
  return null;
}

async function getFileSha(
  token: string,
  owner: string,
  repo: string,
  filePath: string,
  branch: string
): Promise<{ sha: string; content: string } | null> {
  const url = `${GITHUB_API}/repos/${owner}/${repo}/contents/${filePath}?ref=${branch}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return { sha: data.sha, content: Buffer.from(data.content, 'base64').toString('utf-8') };
}

async function putFileContent(
  token: string,
  owner: string,
  repo: string,
  filePath: string,
  branch: string,
  content: string,
  sha: string,
  message: string
): Promise<{ sha: string }> {
  const url = `${GITHUB_API}/repos/${owner}/${repo}/contents/${filePath}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    body: JSON.stringify({
      message,
      content: Buffer.from(content, 'utf-8').toString('base64'),
      sha,
      branch,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `GitHub API error ${res.status}`);
  }

  const result = await res.json();
  return { sha: result.content.sha };
}

export async function POST(req: NextRequest) {
  // --- Auth guard ---
  const token = process.env.GH_PAT;
  if (!token) {
    return NextResponse.json(
      {
        error:
          'GitHub PAT not configured. Set GH_PAT in your environment variables to enable fund management.',
      },
      { status: 401 }
    );
  }

  const repo = process.env.NEXT_PUBLIC_GITHUB_REPO;
  if (!repo || !repo.includes('/')) {
    return NextResponse.json(
      { error: 'NEXT_PUBLIC_GITHUB_REPO must be set to "owner/repo" format' },
      { status: 500 }
    );
  }

  const branch = process.env.NEXT_PUBLIC_GITHUB_BRANCH || 'main';
  const [owner, repoName] = repo.split('/');
  const filePath = 'config/funds.json';

  // --- Parse request ---
  let body: { action: string; fund: Partial<FundConfig> & { id: string } };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { action, fund } = body;
  if (!['add', 'disable', 'enable'].includes(action)) {
    return NextResponse.json({ error: "action must be 'add', 'disable', or 'enable'" }, { status: 400 });
  }
  if (!fund?.id) {
    return NextResponse.json({ error: "fund.id is required" }, { status: 400 });
  }

  // --- Validate for 'add' ---
  if (action === 'add') {
    const err = validateFundConfig(fund as FundConfig);
    if (err) return NextResponse.json({ error: err }, { status: 400 });
  }

  // --- Fetch current funds.json ---
  const current = await getFileSha(token, owner, repoName, filePath, branch);
  if (!current) {
    return NextResponse.json(
      { error: `Could not fetch ${filePath} from GitHub. Check repo name and branch.` },
      { status: 500 }
    );
  }

  let funds: FundConfig[];
  try {
    funds = JSON.parse(current.content);
  } catch {
    return NextResponse.json({ error: 'Could not parse existing funds.json' }, { status: 500 });
  }

  // --- Apply mutation ---
  let commitMessage: string;

  if (action === 'add') {
    const exists = funds.find((f) => f.id === fund.id);
    if (exists) {
      return NextResponse.json(
        { error: `Fund ID '${fund.id}' already exists in config` },
        { status: 400 }
      );
    }
    const newFund: FundConfig = {
      ...(fund as FundConfig),
      enabled: true,
      significant_change_pp: fund.significant_change_pp ?? 0.5,
    };
    funds.push(newFund);
    commitMessage = `feat(config): add fund '${fund.id}' [skip ci]`;
  } else if (action === 'disable') {
    const idx = funds.findIndex((f) => f.id === fund.id);
    if (idx === -1) {
      return NextResponse.json({ error: `Fund '${fund.id}' not found` }, { status: 400 });
    }
    funds[idx].enabled = false;
    commitMessage = `chore(config): disable fund '${fund.id}' [skip ci]`;
  } else {
    // enable
    const idx = funds.findIndex((f) => f.id === fund.id);
    if (idx === -1) {
      return NextResponse.json({ error: `Fund '${fund.id}' not found` }, { status: 400 });
    }
    funds[idx].enabled = true;
    commitMessage = `chore(config): re-enable fund '${fund.id}' [skip ci]`;
  }

  // --- Commit to GitHub ---
  try {
    const newContent = JSON.stringify(funds, null, 2) + '\n';
    const result = await putFileContent(
      token,
      owner,
      repoName,
      filePath,
      branch,
      newContent,
      current.sha,
      commitMessage
    );
    return NextResponse.json({ success: true, sha: result.sha });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: `GitHub commit failed: ${msg}` }, { status: 500 });
  }
}
