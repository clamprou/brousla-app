/**
 * Authentication utilities for both local dev and cloud
 */

const CLOUD_API_URL = process.env.BROUSLA_CLOUD_URL || 'http://localhost:8000';
const ACCESS_TOKEN_KEY = 'brousla_access_token';
const USER_EMAIL_KEY = 'brousla_user_email';
const AUTH_MODE_KEY = 'brousla_auth_mode'; // 'local' or 'cloud'

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  email: string | null;
  accessToken: string | null;
  mode: 'local' | 'cloud';
}

/**
 * Register user with cloud service
 */
export async function registerCloud(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${CLOUD_API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, pwd: password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }

  const data: AuthResponse = await response.json();
  
  // Store auth state
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_EMAIL_KEY, email);
  localStorage.setItem(AUTH_MODE_KEY, 'cloud');
  
  return data;
}

/**
 * Login user with cloud service
 */
export async function loginCloud(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${CLOUD_API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, pwd: password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  const data: AuthResponse = await response.json();
  
  // Store auth state
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_EMAIL_KEY, email);
  localStorage.setItem(AUTH_MODE_KEY, 'cloud');
  
  return data;
}

/**
 * Local dev login (bypasses cloud)
 */
export function loginLocal(email: string): void {
  // For local dev, just store email and generate a fake token
  const fakeToken = `local_dev_${Date.now()}`;
  localStorage.setItem(ACCESS_TOKEN_KEY, fakeToken);
  localStorage.setItem(USER_EMAIL_KEY, email);
  localStorage.setItem(AUTH_MODE_KEY, 'local');
}

/**
 * Register device with cloud service
 */
export async function registerDevice(accessToken: string, deviceId: string, appVersion: string): Promise<void> {
  const response = await fetch(`${CLOUD_API_URL}/devices/register`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ device_id: deviceId, app_version: appVersion }),
  });

  if (!response.ok) {
    console.error('Failed to register device:', response.statusText);
  }
}

/**
 * Get current auth state
 */
export function getAuthState(): AuthState {
  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  const email = localStorage.getItem(USER_EMAIL_KEY);
  const mode = (localStorage.getItem(AUTH_MODE_KEY) as 'local' | 'cloud') || 'local';
  
  return {
    isAuthenticated: !!accessToken && !!email,
    email,
    accessToken,
    mode,
  };
}

/**
 * Logout
 */
export function logout(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(USER_EMAIL_KEY);
  localStorage.removeItem(AUTH_MODE_KEY);
  localStorage.removeItem('brousla_license_jwt');
  localStorage.removeItem('brousla_license_timestamp');
}
