"use client";

import React from "react";
import { AuthProvider } from "@/hooks/useAuth";
import type { Locale } from "@/i18n/config";
import { I18nProvider } from "@/i18n/I18nProvider";

export function Providers({ locale, children }: { locale: Locale; children: React.ReactNode }) {
  return (
    <I18nProvider initialLocale={locale}>
      <AuthProvider>{children}</AuthProvider>
    </I18nProvider>
  );
}
