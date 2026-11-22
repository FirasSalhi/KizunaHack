"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";

/** Address of the HarvestGuard page (research/post-harvest-model), served by app/embed/post-harvest/route.ts. */
const PAGE_URL = "/embed/post-harvest";

export function PostHarvest() {
  const { m, locale } = useI18n();
  const t = m.postHarvest;

  return (
    <div className="flex flex-col h-[calc(100svh-65px)] lg:h-svh">
      <header className="px-6 sm:px-10 pt-6 pb-4 border-b border-white/10 flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div className="max-w-3xl">
          <h1 className="text-2xl font-bold text-white tracking-tight">{t.title}</h1>
          <p className="text-sm text-neutral-400 mt-1">{t.subtitle}</p>
          {locale !== "en" && <p className="text-xs text-[#c6f04a] mt-1.5">{t.englishOnly}</p>}
        </div>
        <a
          href={PAGE_URL}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-xs text-neutral-300 hover:text-white underline underline-offset-4"
        >
          {t.openTab}
        </a>
      </header>

      <div className="relative flex-1 min-h-[520px] bg-[#0a110e]">
        <iframe
          src={PAGE_URL}
          title={t.frameTitle}
          className="absolute inset-0 w-full h-full border-0"
          allow="geolocation"
        />
      </div>
    </div>
  );
}
