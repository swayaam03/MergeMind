/**
 * Authentication & Account Management Service for MergeMind.
 */

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export function getStoredUser() {
  try {
    const raw = localStorage.getItem('mergemind_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user, token) {
  if (user) {
    localStorage.setItem('mergemind_user', JSON.stringify(user));
  }
  if (token) {
    localStorage.setItem('mergemind_token', token);
  }
}

export function clearStoredUser() {
  localStorage.removeItem('mergemind_user');
  localStorage.removeItem('mergemind_token');
}

export function getStoredToken() {
  return localStorage.getItem('mergemind_token');
}

function getAuthHeaders() {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  const token = getStoredToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    headers['X-Session-Token'] = token;
  }
  return headers;
}

export async function registerUser(username, email, password) {
  const response = await fetch(`${BACKEND_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username, email, password }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Registration failed.');
  }

  setStoredUser(data.user, data.token);
  return data;
}

export async function loginUser(username_or_email, password) {
  const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username_or_email, password }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Login failed.');
  }

  setStoredUser(data.user, data.token);
  return data;
}

export async function fetchCurrentUser() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
      method: 'GET',
      headers: getAuthHeaders(),
      credentials: 'include',
    });

    if (!response.ok) {
      if (response.status === 401) {
        clearStoredUser();
      }
      return null;
    }

    const user = await response.json();
    setStoredUser(user);
    return user;
  } catch (err) {
    console.error('Failed to fetch current user:', err);
    return null;
  }
}

export async function connectGitHubInstallation(installation_id) {
  const response = await fetch(`${BACKEND_URL}/api/auth/connect-github`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({ installation_id: Number(installation_id) }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to link GitHub installation.');
  }

  setStoredUser(data);
  return data;
}

export async function disconnectGitHub() {
  const response = await fetch(`${BACKEND_URL}/api/auth/disconnect-github`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to disconnect GitHub.');
  }

  setStoredUser(data);
  return data;
}

export async function logoutUser() {
  try {
    await fetch(`${BACKEND_URL}/api/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
      credentials: 'include',
    });
  } finally {
    clearStoredUser();
  }
}
