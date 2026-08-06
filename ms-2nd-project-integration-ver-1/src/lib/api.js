const configuredBaseUrl = import.meta.env.VITE_API_URL || "";
const API_BASE_URL = configuredBaseUrl.replace(/\/$/, "");

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    let message = `요청에 실패했습니다. (${response.status})`;
    try {
      const body = await response.json();
      message = body?.error?.message || body?.detail || message;
    } catch {
      // Use the status message for non-JSON errors.
    }
    throw new Error(message);
  }
  return response.json();
}
