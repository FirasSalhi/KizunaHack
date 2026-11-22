"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { EmbeddedPage } from "./EmbeddedPage";

/**
 * Market at a glance (research/market-advisor/html/marche_simple.html): top produce at the Tunis wholesale market, the best
 * month to sell, and what to plant by region. Pre-filled with the validated plan's governorate and crops.
 */
export function Market() {
  const { m } = useI18n();
  return <EmbeddedPage frameTitle={m.market.frameTitle} src="/embed/market" background="#0d0f0c" />;
}
