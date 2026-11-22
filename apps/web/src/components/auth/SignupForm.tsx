"use client";

import Link from "next/link";
import React, { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { LOCALES, LOCALE_LABELS } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import type { Messages } from "@/i18n/messages/en";
import { ApiError } from "@/services/apiClient";

/** Show a server error in the interface language, matched by its error code. */
function errorText(err: unknown, errors: Messages["auth"]["errors"]) {
  if (err instanceof ApiError && err.code in errors) return errors[err.code as keyof typeof errors];
  return errors.generic;
}


export function SignupForm() {
  const { signup, loginAsDemo } = useAuth();
  const { m, locale: uiLocale } = useI18n();
  const t = m.auth;
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [farmName, setFarmName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [locale, setLocale] = useState<string>(uiLocale);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!name.trim()) {
      setErrorMessage(t.errors.name);
      return;
    }

    if (password.length < 8) {
      setErrorMessage(t.errors.passwordShort);
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage(t.errors.mismatch);
      return;
    }

    try {
      setIsSubmitting(true);
      await signup({
        name: name.trim(),
        email: email.trim(),
        password,
        farm_name: farmName.trim() || `${name.trim()}'s Farm`,
        locale,
      });
    } catch (err: unknown) {
      setErrorMessage(errorText(err, t.errors));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3.5">
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
        <label
          htmlFor="name"
          className="block text-xs font-medium text-neutral-300 mb-1"
        >
          {t.fields.name}
        </label>
        <input
          id="name"
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t.placeholders.name}
          className="w-full px-3.5 py-2.5 rounded-lg bg-[#1a201c] border border-[#2b352d] text-white placeholder-neutral-500 text-sm focus:outline-none focus:border-[#a3e635] focus:ring-1 focus:ring-[#a3e635] transition-colors"
        />
      </div>

      <div>
        <label
          htmlFor="email"
          className="block text-xs font-medium text-neutral-300 mb-1"
        >
          {t.fields.email}
        </label>
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
        <label
          htmlFor="farmName"
          className="block text-xs font-medium text-neutral-300 mb-1"
        >
          {t.fields.farmName}
        </label>
        <input
          id="farmName"
          type="text"
          value={farmName}
          onChange={(e) => setFarmName(e.target.value)}
          placeholder={t.placeholders.farmName}
          className="w-full px-3.5 py-2.5 rounded-lg bg-[#1a201c] border border-[#2b352d] text-white placeholder-neutral-500 text-sm focus:outline-none focus:border-[#a3e635] focus:ring-1 focus:ring-[#a3e635] transition-colors"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label
            htmlFor="password"
            className="block text-xs font-medium text-neutral-300 mb-1"
          >
            {t.fields.password}
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t.placeholders.password}
            className="w-full px-3 py-2.5 rounded-lg bg-[#1a201c] border border-[#2b352d] text-white placeholder-neutral-500 text-sm focus:outline-none focus:border-[#a3e635] focus:ring-1 focus:ring-[#a3e635] transition-colors"
          />
        </div>
        <div>
          <label
            htmlFor="confirmPassword"
            className="block text-xs font-medium text-neutral-300 mb-1"
          >
            {t.fields.confirm}
          </label>
          <input
            id="confirmPassword"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder={t.placeholders.confirm}
            className="w-full px-3 py-2.5 rounded-lg bg-[#1a201c] border border-[#2b352d] text-white placeholder-neutral-500 text-sm focus:outline-none focus:border-[#a3e635] focus:ring-1 focus:ring-[#a3e635] transition-colors"
          />
        </div>
      </div>

      <div>
        <label
          htmlFor="locale"
          className="block text-xs font-medium text-neutral-300 mb-1"
        >
          {t.fields.language}
        </label>
        <select
          id="locale"
          value={locale}
          onChange={(e) => setLocale(e.target.value)}
          className="w-full px-3.5 py-2.5 rounded-lg bg-[#1a201c] border border-[#2b352d] text-white text-sm focus:outline-none focus:border-[#a3e635] focus:ring-1 focus:ring-[#a3e635] transition-colors"
        >
          {LOCALES.map((code) => (
            <option key={code} value={code} lang={code}>{LOCALE_LABELS[code].name}</option>
          ))}
        </select>
      </div>

      <div className="pt-2">
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2.5 px-4 rounded-lg bg-[#a3e635] hover:bg-[#bef264] active:scale-[0.99] text-[#0c0f0d] font-semibold text-sm transition-all duration-150 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          {isSubmitting ? (
            <>
              <span className="w-4 h-4 border-2 border-[#0c0f0d] border-t-transparent rounded-full animate-spin" />
              {t.creating}
            </>
          ) : (
            t.createButton
          )}
        </button>
      </div>

      <div className="pt-2 border-t border-[#222a23] text-center">
        <button
          type="button"
          onClick={loginAsDemo}
          className="text-xs text-neutral-400 hover:text-[#a3e635] transition-colors"
        >
          {t.demoPrompt} <span className="underline underline-offset-4 text-neutral-300 hover:text-[#a3e635]">{t.demoInstant} <span className="flip-rtl">&rarr;</span></span>
        </button>
      </div>

      <div className="text-center text-xs text-neutral-400">
        {t.already}{" "}
        <Link
          href="/login"
          className="text-[#a3e635] font-medium hover:underline"
        >
          {t.signInLink}
        </Link>
      </div>
    </form>
  );
}
