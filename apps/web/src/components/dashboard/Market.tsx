"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { EmbeddedPage } from "./EmbeddedPage";

/**
 * Market at a glance (research/market-advisor/html/marche_simple.html), in French and Tunisian Arabic:
 * top produce at the Tunis wholesale market (3D stall), the best month to sell, and what to plant by region.
 * Built from official INS and Ministry of Agriculture data by research/market-advisor/scripts/build_simple_dashboard.py.
 */
export function Market() {
  const { m, locale } = useI18n();
  const t = m.market;
  return (
    <EmbeddedPage
      title={t.title}
      subtitle={t.subtitle}
      note={locale !== "fr" && locale !== "ar" ? t.frenchArabicOnly : undefined}
      openTab={t.openTab}
      frameTitle={t.frameTitle}
      src="/embed/market"
      background="#F7F9F7"
    />
  );
}
