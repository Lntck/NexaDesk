/**
 * Access token memory store.
 *
 * The access token lives in memory only (never in localStorage); the refresh
 * token is an HttpOnly cookie owned by the backend. The module exposes a tiny
 * imperative API so the fetch client does not depend on the UI state stores.
 */

let accessToken: string | null = null;

let onUnauthorized: (() => void) | null = null;

/**
 * Store the current access token in memory.
 *
 * @param token JWT access token or null to clear it.
 */
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/**
 * Read the current access token.
 *
 * @returns the stored token or null when the user is not authenticated.
 */
export function getAccessToken(): string | null {
  return accessToken;
}

/**
 * Register a callback fired when a refresh attempt fails.
 *
 * The session layer uses it to clear cached user data and route to login.
 *
 * @param callback function invoked on definitive auth loss, or null to unset.
 */
export function setUnauthorizedHandler(callback: (() => void) | null): void {
  onUnauthorized = callback;
}

/**
 * Notify the registered handler about a lost session.
 */
export function notifyUnauthorized(): void {
  onUnauthorized?.();
}
