/**
 * GitHub integration service for MergeMind.
 * Communicates with backend GitHub API endpoints using secure HttpOnly cookies.
 */

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

/**
 * Check if the active browser has a valid GitHub App installation context.
 * Returns: { connected: boolean, repository_count?: number }
 */
export async function checkGitHubStatus() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/github/status`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      return { connected: false };
    }

    const data = await response.json();
    return {
      connected: Boolean(data.connected),
      repository_count: typeof data.repository_count === 'number' ? data.repository_count : undefined,
    };
  } catch (err) {
    console.error('Error checking GitHub connection status:', err);
    return { connected: false };
  }
}
