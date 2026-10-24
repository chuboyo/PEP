const ACCESS_KEY = "pep_access_token";
const REFRESH_KEY = "pep_refresh_token";

let accessToken: string | null = sessionStorage.getItem(ACCESS_KEY);
let refreshToken: string | null = sessionStorage.getItem(REFRESH_KEY);

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  refreshToken = refresh;
  sessionStorage.setItem(ACCESS_KEY, access);
  sessionStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  accessToken = null;
  refreshToken = null;
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}
