/**
 * Centralized API client for MergeMind frontend.
 * Automatically injects authentication tokens and credentials into every HTTP request.
 */

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export function getAuthHeaders(customHeaders = {}) {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...customHeaders,
  };

  const token = localStorage.getItem('mergemind_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    headers['X-Session-Token'] = token;
  }

  return headers;
}

export async function apiFetch(path, options = {}) {
  const url = path.startsWith('http') ? path : `${BACKEND_URL}${path}`;
  const headers = getAuthHeaders(options.headers || {});

  const config = {
    ...options,
    headers,
    credentials: 'include',
  };

  const response = await fetch(url, config);
  return response;
}

export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || `Request failed with status ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}
