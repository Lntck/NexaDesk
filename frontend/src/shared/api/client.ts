/**
 * JSON API client for the NexaDesk backend.
 *
 * Sends Bearer auth, keeps the refresh cookie, retries once after a silent
 * refresh on 401, parses the error envelope and supports If-Match headers.
 */
import { toApiError } from './errors';
import { getAccessToken, notifyUnauthorized, setAccessToken } from './token';

const API_ORIGIN: string = import.meta.env.VITE_API_URL ?? '';

/**
 * Build a full URL for an API path.
 *
 * @param path path starting with /api or /health.
 * @returns absolute or proxied URL for the request.
 */
function apiUrl(path: string): string {
  return `${API_ORIGIN}${path}`;
}

/**
 * Append query parameters to a path, skipping empty values.
 *
 * @param path request path without query string.
 * @param params record of query parameters; null and undefined are dropped.
 * @returns path with an encoded query string.
 */
export function withQuery(
  path: string,
  params?: Record<string, string | number | boolean | null | undefined>,
): string {
  if (!params) return path;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '') continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `${path}?${qs}` : path;
}

/** Extra request options understood by the API client on top of fetch. */
export interface ApiRequestOptions {
  /** JSON request body; serialized automatically. */
  body?: unknown;
  /** Form encoded request body (used by the login endpoint). */
  form?: Record<string, string>;
  /** Optimistic concurrency version sent as If-Match. */
  ifMatch?: number | string;
  /** Abort signal for cancellation. */
  signal?: AbortSignal;
}

/**
 * Perform an API request and parse the JSON response.
 *
 * Throws ApiError for any non-2xx response.
 *
 * @param method HTTP method.
 * @param path request path starting with /api or /health.
 * @param options request body, form data, If-Match version and abort signal.
 * @returns parsed response body typed as T.
 */
export async function apiRequest<T>(
  method: string,
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const execute = async (retried: boolean): Promise<T> => {
    const headers: Record<string, string> = { Accept: 'application/json' };
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.ifMatch !== undefined) headers['If-Match'] = String(options.ifMatch);

    let body: BodyInit | undefined;
    if (options.form) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
      body = new URLSearchParams(options.form).toString();
    } else if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(options.body);
    }

    const response = await fetch(apiUrl(path), {
      method,
      headers,
      body,
      credentials: 'include',
      signal: options.signal,
    });

    if (response.status === 204) return undefined as T;

    const text = await response.text();
    const parsed: unknown = text ? safeJson(text) : null;

    if (!response.ok) {
      const error = toApiError(response.status, parsed);
      const isAuthPath = path.endsWith('/login') || path.endsWith('/refresh');
      if (response.status === 401 && !retried && !isAuthPath) {
        const refreshed = await tryRefreshToken();
        if (refreshed) return execute(true);
        notifyUnauthorized();
      }
      throw error;
    }
    return parsed as T;
  };

  return execute(false);
}

/**
 * Parse JSON text without throwing on malformed payloads.
 *
 * @param text raw response text.
 * @returns parsed value or the original text when parsing fails.
 */
function safeJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

/**
 * Refresh the access token using the HttpOnly refresh cookie.
 *
 * @returns true when a new access token was issued and stored.
 */
async function tryRefreshToken(): Promise<boolean> {
  try {
    const data = await apiRequest<{ access_token: string }>('POST', '/api/v1/refresh');
    setAccessToken(data.access_token);
    return true;
  } catch {
    setAccessToken(null);
    return false;
  }
}
