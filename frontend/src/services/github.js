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
