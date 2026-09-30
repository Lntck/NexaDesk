/** REST calls for authentication and the current user. */

import { apiRequest } from '@/shared/api/client';
import type { Token, UserRead, UserRegister } from '@/shared/api/types';

/**
 * Register a new account.
 *
 * @param body username, email and password.
 * @returns the created user.
 */
export function register(body: UserRegister): Promise<UserRead> {
  return apiRequest('POST', '/api/v1/register', { body });
}

/**
 * Login with username and password form fields.
 *
 * The refresh token is stored by the backend in an HttpOnly cookie.
 *
 * @param username account name.
 * @param password plain password.
 * @returns access token payload.
 */
export function login(username: string, password: string): Promise<Token> {
  return apiRequest('POST', '/api/v1/login', { form: { username, password } });
}

/**
 * Rotate the refresh cookie and obtain a new access token.
 *
 * @returns access token payload.
 */
export function refreshToken(): Promise<Token> {
  return apiRequest('POST', '/api/v1/refresh');
}

/**
 * Revoke the refresh token and clear the cookie.
 */
export function logout(): Promise<void> {
  return apiRequest('POST', '/api/v1/logout');
}

/**
 * Fetch the profile of the authenticated user.
 *
 * @returns current user data.
 */
export function aboutMe(): Promise<UserRead> {
  return apiRequest('GET', '/api/v1/about_me');
}
