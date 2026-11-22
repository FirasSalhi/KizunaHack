"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/services/authService";
import { clearStoredTokens, getStoredToken, setStoredToken } from "@/services/apiClient";
import type {
  LoginCredentials,
  MeResponse,
  RegisterCredentials,
} from "@/types/auth";

interface AuthContextType {
  user: MeResponse | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (credentials: RegisterCredentials) => Promise<void>;
  loginAsDemo: () => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  const loadCurrentUser = async () => {
    const storedToken = getStoredToken();
    if (!storedToken) {
      setIsLoading(false);
      return;
    }

    setToken(storedToken);

    // If demo token, set demo user directly
    if (storedToken === "demo_access_token_jwt") {
      setUser({
        id: "018f3a22-4a7b-7000-8000-000000000001",
        email: "demo@farmlink.tn",
        name: "Sami Ben Ali (Demo)",
        locale: "fr",
        memberships: [
          {
            farm_id: "018f3a22-4a7b-7000-8000-000000000002",
            farm_name: "El Mornag Vineyard (Demo)",
            role: "owner",
          },
        ],
      });
      setIsLoading(false);
      return;
    }

    try {
      const me = await authService.getMe();
      setUser(me);
    } catch {
      const refreshed = await authService.refreshToken();
      if (refreshed) {
        setToken(refreshed.access_token);
        const me = await authService.getMe();
        setUser(me);
      } else {
        clearStoredTokens();
        setUser(null);
        setToken(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadCurrentUser();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const tokens = await authService.login(credentials);
      setToken(tokens.access_token);
      const me = await authService.getMe();
      setUser(me);
      router.push("/dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (credentials: RegisterCredentials) => {
    setIsLoading(true);
    try {
      const tokens = await authService.register(credentials);
      setToken(tokens.access_token);
      const me = await authService.getMe();
      setUser(me);
      router.push("/dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  const loginAsDemo = () => {
    const demoToken = "demo_access_token_jwt";
    setStoredToken(demoToken);
    setToken(demoToken);
    setUser({
      id: "018f3a22-4a7b-7000-8000-000000000001",
      email: "demo@farmlink.tn",
      name: "Sami Ben Ali (Demo)",
      locale: "fr",
      memberships: [
        {
          farm_id: "018f3a22-4a7b-7000-8000-000000000002",
          farm_name: "El Mornag Vineyard (Demo)",
          role: "owner",
        },
      ],
    });
    router.push("/dashboard");
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      if (token !== "demo_access_token_jwt") {
        await authService.logout();
      }
    } catch {
      // Ignore network errors
    } finally {
      clearStoredTokens();
      setUser(null);
      setToken(null);
      setIsLoading(false);
      router.push("/login");
    }
  };

  const refreshUser = async () => {
    try {
      const me = await authService.getMe();
      setUser(me);
    } catch {
      // Ignore
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        loginAsDemo,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
