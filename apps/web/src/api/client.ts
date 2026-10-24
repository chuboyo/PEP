import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "../auth";

export const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) {
    return false;
  }
  const response = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!response.ok) {
    clearTokens();
    return false;
  }
  const body = (await response.json()) as TokenResponse;
  setTokens(body.access_token, body.refresh_token);
  return true;
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${apiUrl}${path}`, { ...init, headers });
  if (response.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch(path, init, false);
    }
  }
  return response;
}

/** Revoke the current refresh token on the API, then always clear local tokens. */
export async function logoutApi(): Promise<void> {
  const refresh = getRefreshToken();
  if (refresh) {
    try {
      await fetch(`${apiUrl}/api/v1/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
    } catch {
      // Local logout still proceeds if the network call fails.
    }
  }
  clearTokens();
}
