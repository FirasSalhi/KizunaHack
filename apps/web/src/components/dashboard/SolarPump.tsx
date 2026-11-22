"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { EmbeddedPage } from "./EmbeddedPage";

/**
 * 3D simulation (research/solar-pump/html/solaire_3d.html) of a STEG grid outage while solar panels, a battery and an
 * inverter keep the ROOTLOOP irrigation pump running. Pre-filled with the validated plan's governorate, crop and area.
 */
export function SolarPump() {
  const { m } = useI18n();
  return <EmbeddedPage frameTitle={m.solar.frameTitle} src="/embed/solar" background="#0d0f0c" />;
}
