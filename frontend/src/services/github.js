/**
 * GitHub integration service for MergeMind.
 * Communicates with backend GitHub API endpoints using secure HttpOnly cookies and Auth Tokens.
 */

import { apiFetch, apiJson } from './api';

/**
 * Check if the active browser has a valid GitHub App installation context.
 * Returns: { connected: boolean, installation_id?: number, repository_count?: number }
 */
export async function checkGitHubStatus() {
  try {
    const response = await apiFetch('/api/github/status', { method: 'GET' });

    if (!response.ok) {
      return { connected: false };
    }

    const data = await response.json();
    return {
      connected: Boolean(data.connected),
      installation_id: data.installation_id || undefined,
      repository_count: typeof data.repository_count === 'number' ? data.repository_count : undefined,
    };
  } catch (err) {
    console.error('Error checking GitHub connection status:', err);
    return { connected: false };
  }
}

/**
 * Fetch all active installations of the MergeMind GitHub App.
 * Returns: Array of { id, account_login, account_type, avatar_url, html_url }
 */
export async function fetchAllInstallations() {
  try {
    const data = await apiJson('/api/github/installations');
    return data.installations || [];
  } catch (err) {
    console.error('Error fetching GitHub App installations:', err);
    return [];
  }
}

/**
 * Submit human decision (accept, edit, or reject) on a proposed merge resolution.
 */
export async function submitMergeDecision(owner, repo, pullNumber, decisionData, runId = null) {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : '';
  return apiJson(`/api/github/repositories/${owner}/${repo}/pulls/${pullNumber}/decision${query}`, {
    method: 'POST',
    body: JSON.stringify(decisionData),
  });
}

/**
 * Fetch past merge runs and human decisions for a pull request.
 */
export async function fetchMergeRuns(owner, repo, pullNumber) {
  try {
    return await apiJson(`/api/github/repositories/${owner}/${repo}/pulls/${pullNumber}/merge-runs`);
  } catch (err) {
    console.warn('Failed to fetch past merge runs:', err);
    return [];
  }
}


