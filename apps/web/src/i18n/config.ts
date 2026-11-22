// Interface languages: French (default), Tunisian Arabic / Derja (Arabic script, right-to-left), English, Japanese.
// The codes match what the API stores in `user.locale` (en | fr | ar | ja).
export const LOCALES = ["fr", "ar", "en", "ja"] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "fr";
export const LOCALE_COOKIE = "fl_locale";

export const LOCALE_LABELS: Record<Locale, { short: string; name: string }> = {
  fr: { short: "FR", name: "Français" },
  ar: { short: "عربي", name: "العربية / الدارجة" },
  en: { short: "EN", name: "English" },
  ja: { short: "JA", name: "日本語" },
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function dirOf(locale: Locale): "rtl" | "ltr" {
  return locale === "ar" ? "rtl" : "ltr";
}

/** Pick a language from the saved cookie, else from the browser's Accept-Language header, else French. */
export function resolveLocale(cookieValue: string | undefined, acceptLanguage: string | null): Locale {
  if (isLocale(cookieValue)) return cookieValue;
  const preferred = (acceptLanguage ?? "")
    .split(",")
    .map((part) => part.trim().slice(0, 2).toLowerCase());
  return preferred.find(isLocale) ?? DEFAULT_LOCALE;
}
