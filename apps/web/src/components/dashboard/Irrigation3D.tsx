"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { EmbeddedPage } from "./EmbeddedPage";

/**
 * The 3D farm (research/irrigation-notebook/html/ferme_3d.html), French only. With the FARMLINK API running on
 * :8001 it uses the real irrigation engine and today's weather; otherwise it runs its built-in demo.
 */
export function Irrigation3D() {
  const { m, locale } = useI18n();
  const t = m.irrigation3d;
  return (
    <EmbeddedPage
      title={t.title}
      subtitle={t.subtitle}
      note={locale !== "fr" ? t.frenchOnly : undefined}
      openTab={t.openTab}
      frameTitle={t.frameTitle}
      src="/embed/irrigation-3d"
      background="#0d100d"
    />
  );
}
