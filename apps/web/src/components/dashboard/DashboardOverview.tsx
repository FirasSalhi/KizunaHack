"use client";

import React from "react";
import { useAuth } from "@/hooks/useAuth";
import { fill, useI18n } from "@/i18n/I18nProvider";
import { FieldSensors } from "./FieldSensors";

/** Dashboard home: a greeting and the field unit's live readings (firmware/field-unit). */
export function DashboardOverview() {
  const { user } = useAuth();
  const { m } = useI18n();
  const t = m.dashboard;
  const primaryFarm = user?.memberships?.[0]?.farm_name || "El Mornag Vineyard";

  return (
    <div className="p-5 sm:p-10 max-w-6xl mx-auto space-y-8">
      <header className="pb-6 border-b border-white/10">
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          {fill(t.welcome, { name: user?.name || t.farmer })}
        </h1>
        <p className="text-sm text-neutral-400 mt-1">{fill(t.monitoring, { farm: primaryFarm })}</p>
      </header>

      <FieldSensors />
    </div>
  );
}
