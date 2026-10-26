import type { paths } from "./schema";
import { apiFetch, apiUrl } from "./client";

export type MeResponse =
  paths["/api/v1/me"]["get"]["responses"]["200"]["content"]["application/json"];

export type TokenPair = {
  access_token: string;
  refresh_token: string;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function login(email: string, password: string): Promise<TokenPair> {
  const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new ApiError(
      response.status,
      response.status === 401 ? "Invalid credentials" : `HTTP ${response.status}`,
    );
  }
  return (await response.json()) as TokenPair;
}

export async function fetchMe(): Promise<MeResponse> {
  const response = await apiFetch("/api/v1/me");
  if (!response.ok) {
    throw new ApiError(response.status, `HTTP ${response.status}`);
  }
  return (await response.json()) as MeResponse;
}

export async function acceptInvite(
  token: string,
  password: string,
): Promise<TokenPair> {
  const response = await fetch(`${apiUrl}/api/v1/auth/accept-invite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, password }),
  });
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      // keep status message
    }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as TokenPair;
}
