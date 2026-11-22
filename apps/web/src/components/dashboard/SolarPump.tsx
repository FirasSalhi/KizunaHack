"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { EmbeddedPage } from "./EmbeddedPage";

/**
 * 3D simulation (research/solar-pump/html/solaire_3d.html), French with Arabic headlines: a STEG grid outage while
 * solar panels, a battery and an automatic inverter keep the ROOTLOOP subsurface irrigation pump running.
 * Sunlight per governorate comes from NASA POWER; the water need from FAO-56.
 */
export function SolarPump() {
  const { m, locale } = useI18n();
  const t = m.solar;
  return (
    <EmbeddedPage
      title={t.title}
      subtitle={t.subtitle}
      note={locale !== "fr" && locale !== "ar" ? t.frenchOnly : undefined}
      openTab={t.openTab}
      frameTitle={t.frameTitle}
      src="/embed/solar"
      background="#090b08"
    />
  );
}
