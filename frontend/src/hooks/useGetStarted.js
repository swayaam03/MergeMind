import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { checkGitHubStatus } from '../services/github';

/**
 * Hook to handle the "Get Started" click flow:
 * 1. Queries backend GET /api/github/status to verify installation context.
 * 2. If connected -> navigates directly to /repositories.
 * 3. If not connected -> navigates to /connect.
 * Does not force already-connected users through installation again.
 */
export function useGetStarted() {
  const [checking, setChecking] = useState(false);
  const navigate = useNavigate();

  const handleGetStarted = async (e) => {
    if (e && typeof e.preventDefault === 'function') {
      e.preventDefault();
    }
    if (checking) return;

    setChecking(true);
    try {
      const status = await checkGitHubStatus();
      if (status && status.connected) {
        navigate('/repositories');
      } else {
        navigate('/connect');
      }
    } catch (err) {
      console.error('Failed checking GitHub status during Get Started:', err);
      navigate('/connect');
    } finally {
      setChecking(false);
    }
  };

  return { handleGetStarted, checking };
}
