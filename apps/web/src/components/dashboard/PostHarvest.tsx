"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { POST_HARVEST_CROP } from "@/lib/farmPlan";
import { EmbeddedPage } from "./EmbeddedPage";
import { PlanSummary, useFarmPlan } from "./PlanSummary";

/** HarvestGuard post-harvest storage page (research/post-harvest-model), English only. */
export function PostHarvest() {
  const { m, locale } = useI18n();
  const plan = useFarmPlan();
  const t = m.postHarvest;
  return (
    <EmbeddedPage
      title={t.title}
      subtitle={t.subtitle}
      note={locale !== "en" ? t.englishOnly : undefined}
      openTab={t.openTab}
      frameTitle={t.frameTitle}
      src="/embed/post-harvest"
      extra={<PlanSummary variant="tool" usable={!plan || plan.crops.some((c) => c.id in POST_HARVEST_CROP)} />}
      background="#0a110e"
    />
  );
}
