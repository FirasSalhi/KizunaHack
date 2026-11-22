"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { EmbeddedPage } from "./EmbeddedPage";

/** HarvestGuard post-harvest storage page (research/post-harvest-model), English only. */
export function PostHarvest() {
  const { m, locale } = useI18n();
  const t = m.postHarvest;
  return (
    <EmbeddedPage
      title={t.title}
      subtitle={t.subtitle}
      note={locale !== "en" ? t.englishOnly : undefined}
      openTab={t.openTab}
      frameTitle={t.frameTitle}
      src="/embed/post-harvest"
      background="#0a110e"
    />
  );
}
