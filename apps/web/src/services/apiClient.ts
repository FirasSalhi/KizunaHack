export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(message: string, status: number, code: string = "API_ERROR", details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface RawErrorBody {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
  detail?:
    | string
    | { error?: { code?: string; message?: string; details?: Record<string, unknown> } }
    | ValidationIssue[];
}

/** One entry of FastAPI's 422 response: {"detail": [{"loc": ["body", "email"], "msg": "...", "type": "..."}]} */
interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
  ctx?: { min_length?: number; max_length?: number };
}

const FIELD_LABELS: Record<string, string> = {
  email: "Email",
  password: "Password",
  name: "Name",
  farm_name: "Farm name",
  locale: "Language",
};

/** Turn FastAPI validation issues into one sentence a farmer can act on. */
function describeValidation(issues: ValidationIssue[]): string {
  const sentences = issues.map((issue) => {
    const field = String(issue.loc?.[issue.loc.length - 1] ?? "");
    const label = FIELD_LABELS[field] ?? "This field";
    if (field === "email") return "Please enter a valid email address.";
    if (issue.type === "string_too_short" && issue.ctx?.min_length) {
      return `${label} must be at least ${issue.ctx.min_length} characters.`;
    }
    if (issue.type === "string_too_long" && issue.ctx?.max_length) {
      return `${label} must be at most ${issue.ctx.max_length} characters.`;
    }
    return `${label}: ${issue.msg ?? "invalid value"}.`;
  });
  return Array.from(new Set(sentences)).join(" ");
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("fl_access_token");
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("fl_access_token", token);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("fl_refresh_token");
}

export function setStoredRefreshToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("fl_refresh_token", token);
}

export function clearStoredTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("fl_access_token");
  localStorage.removeItem("fl_refresh_token");
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (netErr: unknown) {
    const errorMsg = netErr instanceof Error ? netErr.message : "Network request failed";
    throw new ApiError(
      "Can't reach the Mdhalla server. Check your connection and try again.",
      0,
      "NETWORK_ERROR",
      { cause: errorMsg, apiBaseUrl: API_BASE_URL }
    );
  }

  if (!response.ok) {
    let errorCode = "UNKNOWN_ERROR";
    let errorMessage = `Request failed with status ${response.status}`;
    let details: Record<string, unknown> | undefined;

    try {
      const errData = (await response.json()) as RawErrorBody;
      const detail = errData?.detail;
      if (errData && errData.error) {
        errorCode = errData.error.code || errorCode;
        errorMessage = errData.error.message || errorMessage;
        details = errData.error.details;
      } else if (Array.isArray(detail)) {
        errorCode = "VALIDATION_ERROR";
        errorMessage = describeValidation(detail);
      } else if (typeof detail === "string") {
        errorMessage = detail;
      } else if (detail && detail.error) {
        errorCode = detail.error.code || errorCode;
        errorMessage = detail.error.message || errorMessage;
        details = detail.error.details;
      }
    } catch {
      // Body is not JSON
    }

    throw new ApiError(errorMessage, response.status, errorCode, details);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
