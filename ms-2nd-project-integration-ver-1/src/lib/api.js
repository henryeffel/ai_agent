const configuredBaseUrl = import.meta.env.VITE_API_URL || "";
const API_BASE_URL = configuredBaseUrl.replace(/\/$/, "");

export class ApiRequestError extends Error {
  constructor(message, { status, code, retryable }) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
  }
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    let message = `요청에 실패했습니다. (${response.status})`;
    let code = "http_error";
    let retryable = false;
    try {
      const body = await response.json();
      message = body?.error?.message || body?.detail || message;
      code = body?.error?.code || code;
      retryable = body?.error?.retryable === true;
    } catch {
      // Use the status message for non-JSON errors.
    }
    throw new ApiRequestError(message, { status: response.status, code, retryable });
  }
  return response.json();
}

export async function createGroundedPlanWithRetry(payload, onRetry) {
  const request = () => apiRequest("/api/v1/action-plans/grounded", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  try {
    return await request();
  } catch (error) {
    const canRetry = error.retryable && [502, 503].includes(error.status);
    if (!canRetry) throw error;
    onRetry?.();
    return request();
  }
}
