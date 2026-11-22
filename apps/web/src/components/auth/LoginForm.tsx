"use client";

import Link from "next/link";
import React, { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n/I18nProvider";
import type { Messages } from "@/i18n/messages/en";
import { ApiError } from "@/services/apiClient";

/** Show a server error in the interface language, matched by its error code. */
function errorText(err: unknown, errors: Messages["auth"]["errors"]) {
  if (err instanceof ApiError && err.code in errors) return errors[err.code as keyof typeof errors];
  return errors.generic;
}


export function LoginForm() {
  const { login, loginAsDemo } = useAuth();
  const { m } = useI18n();
  const t = m.auth;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email || !password) {
      setErrorMessage(t.errors.missing);
      return;
    }

    try {
      setIsSubmitting(true);
      await login({ email, password });
    } catch (err: unknown) {
      setErrorMessage(errorText(err, t.errors));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFillDemo = () => {
    setEmail("sami@farmlink.tn");
    setPassword("FarmPassword2026!");
    setErrorMessage(null);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {errorMessage && (
        <div
          role="alert"
          className="p-3 rounded-lg bg-[#241313] border border-[#4a1c1c] text-[#fca5a5] text-xs flex items-start gap-2.5"
        >
          <span className="text-red-400 font-bold mt-0.5" aria-hidden="true">
            &bull;
          </span>
          <div className="flex-1 leading-relaxed">{errorMessage}</div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label
            htmlFor="email"
            className="block text-xs font-medium text-neutral-300"
          >
            {t.fields.email}
          </label>
          <button
            type="button"
            onClick={handleFillDemo}
            className="text-[11px] text-[#a3e635] hover:underline"
          >
            {t.fillTest}
          </button>
        </div>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="farmer@farmlink.tn"
          className="w-full px-3.5 py-2.5 rounded-lg bg-[#1a201c] border border-[#2b352d] text-white placeholder-neutral-500 text-sm focus:outline-none focus:border-[#a3e635] focus:ring-1 focus:ring-[#a3e635] transition-colors"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label
            htmlFor="password"
            className="block text-xs font-medium text-neutral-300"
          >
            {t.fields.password}
          </label>
          <a
            href="#forgot-password"
            onClick={(e) => {
              e.preventDefault();
              alert(t.resetHelp);
            }}
            className="text-xs text-neutral-400 hover:text-white transition-colors"
          >
            {t.forgot}
          </a>
        </div>
        <div className="relative">
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full px-3.5 py-2.5 rounded-lg bg-[#1a201c] border border-[#2b352d] text-white placeholder-neutral-500 text-sm focus:outline-none focus:border-[#a3e635] focus:ring-1 focus:ring-[#a3e635] transition-colors pe-14"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 end-0 pe-3 flex items-center text-xs text-neutral-400 hover:text-white select-none"
            aria-label={showPassword ? t.hidePassword : t.showPassword}
          >
            {showPassword ? t.hide : t.show}
          </button>
        </div>
      </div>

      <div className="flex items-center pt-1">
        <label className="flex items-center gap-2 cursor-pointer text-xs text-neutral-400 select-none">
          <input
            type="checkbox"
            defaultChecked
            className="rounded border-[#2b352d] bg-[#1a201c] text-[#a3e635] focus:ring-0"
          />
          {t.remember}
        </label>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-3 px-4 rounded-xl bg-[#a3e635] hover:bg-[#bef264] active:scale-[0.99] text-[#0c0f0d] font-semibold text-sm transition-all duration-150 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_1px_2px_rgba(0,0,0,0.2),0_2px_8px_rgba(163,230,53,0.15)] hover:shadow-[0_4px_16px_rgba(163,230,53,0.25)] border border-[#84cc16]/50"
      >
        {isSubmitting ? (
          <>
            <span className="w-4 h-4 border-2 border-[#0c0f0d] border-t-transparent rounded-full animate-spin" />
            {t.signingIn}
          </>
        ) : (
          <>
            <span>{t.signInButton}</span>
            <span aria-hidden="true">&rarr;</span>
          </>
        )}
      </button>

      {/* Tasteful, quiet demo option */}
      <div className="pt-3 border-t border-[#222a23] text-center">
        <button
          type="button"
          onClick={loginAsDemo}
          className="text-xs text-neutral-400 hover:text-[#a3e635] transition-colors"
        >
          {t.demoPrompt} <span className="underline underline-offset-4 text-neutral-300 hover:text-[#a3e635]">{t.demoEnter} <span className="flip-rtl">&rarr;</span></span>
        </button>
      </div>

      <div className="pt-1 text-center text-xs text-neutral-400">
        {t.newHere}{" "}
        <Link
          href="/signup"
          className="text-[#a3e635] font-medium hover:underline"
        >
          {t.register}
        </Link>
      </div>
    </form>
  );
}
