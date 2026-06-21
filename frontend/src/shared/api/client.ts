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

export async function postFormWithSession<T>(
  path: string,
  formData: FormData,
  sessionToken: string,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
    headers: sessionHeaders(sessionToken),
  });
  const envelope = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || !envelope.success) {
    const error = envelope.error;
    throw new ApiError(error?.message || "Request failed", error?.code, error?.details, error?.request_id);
  }
  return envelope.data as T;
}

export async function downloadWithSession(path: string, sessionToken: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: sessionHeaders(sessionToken),
  });
  if (!response.ok) {
    const envelope = (await response.json()) as ApiEnvelope<unknown>;
    throw new ApiError(
      envelope.error?.message || "Download failed",
      envelope.error?.code,
      envelope.error?.details,
      envelope.error?.request_id,
    );
  }
  return response.blob();
}

export function putJsonWithSession<T>(
  path: string,
  payload: unknown,
  sessionToken: string,
): Promise<T> {
  return apiRequest<T>(path, {
    method: "PUT",
    body: JSON.stringify(payload),
    headers: sessionHeaders(sessionToken),
  });
}

export function deleteJsonWithSession<T>(path: string, sessionToken: string): Promise<T> {
  return apiRequest<T>(path, {
    method: "DELETE",
    headers: sessionHeaders(sessionToken),
  });
}
