/** Typed errors for failed API calls with the backend error envelope. */

/**
 * Typed error for failed API calls.
 *
 * The backend error envelope carries a human readable `detail` and a stable
 * machine readable `code` (docs/api-endpoints.md, section 4). Validation
 * errors from FastAPI arrive as an array of field violations instead and are
 * flattened into a readable message.
 */
export class ApiError extends Error {
  /** HTTP status code of the failed response. */
  readonly status: number;
  /** Stable error code from the backend registry, if provided. */
  readonly code: string | undefined;
  /** Field-level violations for 422 responses. */
  readonly fields: Record<string, string> | undefined;

  /**
   * Build an API error.
   *
   * @param status HTTP status code.
   * @param message human readable detail.
   * @param code stable backend error code.
   * @param fields field-level validation messages keyed by field name.
   */
  constructor(status: number, message: string, code?: string, fields?: Record<string, string>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

/**
 * Parse an error response body into an ApiError.
 *
 * @param status HTTP status code of the response.
 * @param body parsed JSON body of the response, if any.
 * @returns ApiError with detail, code and optional field violations.
 */
export function toApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === 'object') {
    const envelope = body as { detail?: unknown; code?: unknown };
    const code = typeof envelope.code === 'string' ? envelope.code : undefined;
    if (Array.isArray(envelope.detail)) {
      const fields: Record<string, string> = {};
      const messages: string[] = [];
      for (const item of envelope.detail as Array<{ loc?: unknown[]; msg?: unknown }>) {
        const path = Array.isArray(item.loc)
          ? item.loc.filter((part) => part !== 'body').join('.')
          : '';
        const msg = typeof item.msg === 'string' ? item.msg : 'Invalid value';
        if (path) fields[path] = msg;
        messages.push(path ? `${path}: ${msg}` : msg);
      }
      return new ApiError(
        status,
        messages.join('; ') || 'Validation error',
        'validation_error',
        fields,
      );
    }
    if (typeof envelope.detail === 'string') {
      return new ApiError(status, envelope.detail, code);
    }
    if (typeof envelope.code === 'string') {
      return new ApiError(status, 'Request failed', envelope.code);
    }
  }
  return new ApiError(status, `Request failed with status ${status}`);
}

/**
 * Convert an unknown thrown value into an ApiError.
 *
 * @param error any caught value.
 * @returns ApiError; network failures are reported with status 0.
 */
export function asApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  const message = error instanceof Error ? error.message : 'Network error';
  return new ApiError(0, message);
}

/**
 * Extract a displayable message from any thrown value.
 *
 * @param error any caught value.
 * @returns human readable message for toasts and inline errors.
 */
export function errorMessage(error: unknown): string {
  return asApiError(error).message;
}
