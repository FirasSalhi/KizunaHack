import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LoginPage from "@/app/(auth)/login/page";
import SignupPage from "@/app/(auth)/signup/page";
import { AuthProvider } from "@/hooks/useAuth";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

describe("Auth Pages", () => {
  it("renders login page with email, password fields and submission button", () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    expect(screen.getByRole("heading", { name: /Sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign In to Farm Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Register your farm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Enter Demo Mode/i })).toBeInTheDocument();
  });

  it("renders signup page with full registration inputs and language preference", () => {
    render(
      <AuthProvider>
        <SignupPage />
      </AuthProvider>
    );

    expect(screen.getByRole("heading", { name: /Initialize your smart farm/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Farm \/ Property Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confirm/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Preferred Language/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create Farm Account/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Sign in to your farm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Instant Demo/i })).toBeInTheDocument();
  });
});
