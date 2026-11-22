"use client";

import React from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { useI18n } from "@/i18n/I18nProvider";

/** Shown by the service worker when a page can't load without a connection. */
export default function OfflinePage() {
  const { m } = useI18n();
  const t = m.pwa;
  return (
    <main className="min-h-svh bg-[#090b08] text-white grid place-items-center p-6">
      <div className="max-w-sm text-center space-y-4">
        <BrandLogo size={56} className="mx-auto rounded-2xl" />
        <h1 className="text-xl font-bold">{t.offlineTitle}</h1>
        <p className="text-sm text-neutral-400">{t.offlineText}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="px-5 py-2.5 rounded-lg bg-[#c6f04a] hover:bg-[#b5e03b] text-[#0d0f0c] text-sm font-semibold"
        >
          {t.retry}
        </button>
      </div>
    </main>
  );
}
