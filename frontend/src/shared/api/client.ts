import type { ApiEnvelope } from "../types/auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export class ApiError extends Error {
  code: string;
  details: unknown;
  requestId?: string;

  constructor(message: string, code = "API_ERROR", details?: unknown, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const envelope = (await response.json()) as ApiEnvelope<T>;

  if (!response.ok || !envelope.success) {
    const error = envelope.error;
    throw new ApiError(
      error?.message || "Request failed",
      error?.code,
      error?.details,
      error?.request_id,
    );
  }

  return envelope.data as T;
}

export function postJson<T>(path: string, payload: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function sessionHeaders(sessionToken: string) {
  return {
    "X-Session-Token": sessionToken,
  };
}

export function getJsonWithSession<T>(path: string, sessionToken: string): Promise<T> {
  return apiRequest<T>(path, {
    headers: sessionHeaders(sessionToken),
  });
}

export function postJsonWithSession<T>(
  path: string,
  payload: unknown,
  sessionToken: string,
): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: sessionHeaders(sessionToken),
  });
}
