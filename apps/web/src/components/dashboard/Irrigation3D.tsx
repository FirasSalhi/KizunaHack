"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { EmbeddedPage } from "./EmbeddedPage";

/**
 * The farmer's 3D farm with per-field irrigation decisions (research/irrigation-notebook/html/ferme_3d.html), pre-filled with the validated crop plan.
 */
export function Irrigation3D() {
  const { m } = useI18n();
  return <EmbeddedPage frameTitle={m.irrigation3d.frameTitle} src="/embed/irrigation-3d" background="#0d100d" />;
}
