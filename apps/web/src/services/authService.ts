import {
  apiClient,
  clearStoredTokens,
  getStoredRefreshToken,
  setStoredRefreshToken,
  setStoredToken,
} from "./apiClient";
import type {
  AuthTokens,
  LoginCredentials,
  MeResponse,
  RegisterCredentials,
} from "@/types/auth";

export const authService = {
  async register(credentials: RegisterCredentials): Promise<AuthTokens> {
    const tokens = await apiClient<AuthTokens>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    setStoredToken(tokens.access_token);
    setStoredRefreshToken(tokens.refresh_token);
    return tokens;
  },

  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    const tokens = await apiClient<AuthTokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    setStoredToken(tokens.access_token);
    setStoredRefreshToken(tokens.refresh_token);
    return tokens;
  },

  async getMe(): Promise<MeResponse> {
    return apiClient<MeResponse>("/me", {
      method: "GET",
    });
  },

  async refreshToken(): Promise<AuthTokens | null> {
    const refresh = getStoredRefreshToken();
    if (!refresh) return null;

    try {
      const tokens = await apiClient<AuthTokens>("/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh }),
      });
      setStoredToken(tokens.access_token);
      setStoredRefreshToken(tokens.refresh_token);
      return tokens;
    } catch {
      clearStoredTokens();
      return null;
    }
  },

  async logout(): Promise<void> {
    const refresh = getStoredRefreshToken();
    try {
      await apiClient<{ ok: boolean }>("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh }),
      });
    } catch {
      // Ignore network errors on logout
    } finally {
      clearStoredTokens();
    }
  },
};
