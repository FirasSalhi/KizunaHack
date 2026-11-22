export type UserRole = "owner" | "operator" | "viewer";

export interface FarmMembership {
  farm_id: string;
  farm_name: string;
  role: UserRole;
}

export interface User {
  id: string;
  email: string;
  name: string;
  locale: "en" | "fr" | "ar" | string;
  created_at?: string;
  disabled_at?: string | null;
}

export interface MeResponse extends User {
  memberships: FarmMembership[];
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  name: string;
  email: string;
  password: string;
  farm_name?: string;
  locale?: string;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
