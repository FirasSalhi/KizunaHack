"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { DEFAULT_LOCALE, dirOf, LOCALE_COOKIE, type Locale } from "./config";
import ar from "./messages/ar";
import en, { type Messages } from "./messages/en";
import fr from "./messages/fr";
import ja from "./messages/ja";

const CATALOGS: Record<Locale, Messages> = { fr, ar, en, ja };

interface I18nValue {
  locale: Locale;
  dir: "rtl" | "ltr";
  /** The interface text for the current language, e.g. `m.landing.hero.title`. */
  m: Messages;
  setLocale: (locale: Locale) => void;
}

// Without a provider (e.g. in unit tests) components fall back to English.
const I18nContext = createContext<I18nValue>({ locale: "en", dir: "ltr", m: en, setLocale: () => undefined });

export function I18nProvider({ initialLocale = DEFAULT_LOCALE, children }: { initialLocale?: Locale; children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    // Remembered for a year; the server reads it so the first paint is already in this language.
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
    document.documentElement.lang = next;
    document.documentElement.dir = dirOf(next);
  }, []);

  const value = useMemo(() => ({ locale, dir: dirOf(locale), m: CATALOGS[locale], setLocale }), [locale, setLocale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}

/** Fill {placeholders} in a message: fill("Welcome back, {name}", { name: "Amel" }). */
export function fill(text: string, values: Record<string, string | number>) {
  return text.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? ""));
}

/** Render a message that contains "\n" line breaks. */
export function Lines({ text }: { text: string }) {
  const parts = text.split("\n");
  return (
    <>
      {parts.map((part, i) => (
        <React.Fragment key={i}>
          {i > 0 && <br />}
          {part}
        </React.Fragment>
      ))}
    </>
  );
}
