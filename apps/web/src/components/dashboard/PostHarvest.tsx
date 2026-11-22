"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { EmbeddedPage } from "./EmbeddedPage";

/**
 * HarvestGuard post-harvest storage page (research/post-harvest-model), pre-filled with the validated crop plan.
 */
export function PostHarvest() {
  const { m } = useI18n();
  return <EmbeddedPage frameTitle={m.postHarvest.frameTitle} src="/embed/post-harvest" background="#0a110e" />;
}
