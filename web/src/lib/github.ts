/**
 * github.ts — Client-side helpers for fund config mutations.
 * All actual GitHub API calls are proxied through /api/github/update-fund
 * so that GH_PAT never reaches the browser.
 */

import { FundConfig } from '@/types';

export type { FundConfig };

export interface GithubApiResult {
  success: boolean;
  error?: string;
  sha?: string;
}

/** Returns true if the public GitHub repo env var is configured. */
export function isGitHubConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_GITHUB_REPO);
}

export async function verifyAdminPasscode(passcode: string): Promise<boolean> {
  try {
    const res = await fetch('/api/admin/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ passcode }),
    });
    const data = await res.json();
    return Boolean(data.authenticated);
  } catch {
    return false;
  }
}

async function callUpdateFund(
  action: 'add' | 'disable' | 'enable',
  fund: Partial<FundConfig> & { id: string }
): Promise<GithubApiResult> {
  try {
    const adminKey = typeof window !== 'undefined' ? sessionStorage.getItem('admin_passcode') || '' : '';
    const res = await fetch('/api/github/update-fund', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-admin-key': adminKey,
      },
      body: JSON.stringify({ action, fund }),
    });

    const data = await res.json();

    if (!res.ok) {
      return { success: false, error: data.error || `HTTP ${res.status}` };
    }

    return { success: true, sha: data.sha };
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Network error',
    };
  }
}

/** Add a new fund to config/funds.json via GitHub Contents API. */
export async function addFund(fund: FundConfig): Promise<GithubApiResult> {
  return callUpdateFund('add', fund);
}

/** Soft-delete: set enabled=false for the given fund id. */
export async function disableFund(id: string): Promise<GithubApiResult> {
  return callUpdateFund('disable', { id });
}

/** Re-enable: set enabled=true for the given fund id. */
export async function enableFund(id: string): Promise<GithubApiResult> {
  return callUpdateFund('enable', { id });
}
