import { NextRequest, NextResponse } from 'next/server';

const GITHUB_API = 'https://api.github.com';
const MONTH_REGEX = /^\d{4}-(0[1-9]|1[0-2])$/;
const FUND_ID_REGEX = /^[a-z0-9-]+$/;

export async function POST(req: NextRequest) {
  // 1. Auth Guard (Server-Side GH_PAT)
  const token = process.env.GH_PAT;
  if (!token) {
    return NextResponse.json(
      { error: 'Backfill service is currently unavailable. Administrator configuration required.' },
      { status: 503 }
    );
  }

  // 2. Repo & Branch Config
  const repo = process.env.NEXT_PUBLIC_GITHUB_REPO || 'vedantnathani/fund-ui';
  if (!repo.includes('/')) {
    return NextResponse.json(
      { error: 'Repository configuration is invalid.' },
      { status: 500 }
    );
  }

  const branch = process.env.NEXT_PUBLIC_GITHUB_BRANCH || 'main';
  const [owner, repoName] = repo.split('/');

  // 3. Parse and Validate Request Body
  let body: {
    fund_id?: string;
    start_month?: string;
    end_month?: string;
    dry_run?: boolean;
  };

  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON request payload.' }, { status: 400 });
  }

  const { fund_id, start_month, end_month, dry_run = false } = body;

  if (!fund_id || (fund_id !== 'all' && !FUND_ID_REGEX.test(fund_id))) {
    return NextResponse.json(
      { error: 'Invalid scheme identifier. Must be a valid fund ID or "all".' },
      { status: 400 }
    );
  }

  if (!start_month || !MONTH_REGEX.test(start_month)) {
    return NextResponse.json(
      { error: 'Start month must be in YYYY-MM format (e.g. 2024-01).' },
      { status: 400 }
    );
  }

  if (!end_month || !MONTH_REGEX.test(end_month)) {
    return NextResponse.json(
      { error: 'End month must be in YYYY-MM format (e.g. 2024-06).' },
      { status: 400 }
    );
  }

  if (start_month > end_month) {
    return NextResponse.json(
      { error: `Start month (${start_month}) cannot be after end month (${end_month}).` },
      { status: 400 }
    );
  }

  // 4. Dispatch GitHub Actions workflow
  const workflowId = 'backfill.yml';
  const url = `${GITHUB_API}/repos/${owner}/${repoName}/actions/workflows/${workflowId}/dispatches`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      body: JSON.stringify({
        ref: branch,
        inputs: {
          fund_id,
          start_month,
          end_month,
          dry_run: Boolean(dry_run),
        },
      }),
    });

    if (res.status === 204) {
      return NextResponse.json({
        success: true,
        run_url: `https://github.com/${owner}/${repoName}/actions/workflows/${workflowId}`,
      });
    }

    const errorData = await res.json().catch(() => ({}));
    return NextResponse.json(
      { error: errorData.message || `GitHub Actions dispatch failed with HTTP ${res.status}` },
      { status: res.status >= 400 && res.status < 500 ? res.status : 500 }
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown network failure';
    return NextResponse.json({ error: `Failed to trigger backfill: ${msg}` }, { status: 500 });
  }
}
