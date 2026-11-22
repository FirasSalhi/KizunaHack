"use client";

import React, { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { IconDrop } from "@/components/icons";
import { fill, useI18n } from "@/i18n/I18nProvider";

export function DashboardOverview() {
  const { user } = useAuth();
  const { m } = useI18n();
  const t = m.dashboard;
  const [irrigationStatus, setIrrigationStatus] = useState<"idle" | "cycling" | "completed">("idle");
  const [lastWaterAmount, setLastWaterAmount] = useState<number>(380);

  const primaryFarm = user?.memberships?.[0]?.farm_name || "El Mornag Vineyard";

  const handleTriggerCycle = () => {
    setIrrigationStatus("cycling");
    setTimeout(() => {
      setIrrigationStatus("completed");
      setLastWaterAmount((prev) => prev + 120);
      setTimeout(() => setIrrigationStatus("idle"), 3000);
    }, 2000);
  };

  return (
    <div className="p-6 sm:p-10 max-w-7xl mx-auto space-y-8">
      {/* Top Banner Greeting */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-wider text-[#c6f04a] bg-[#c6f04a]/10 px-2.5 py-0.5 rounded-full border border-[#c6f04a]/20">
              {t.live}
            </span>
            <span className="text-neutral-500 text-xs font-mono">•</span>
            <span className="text-xs font-mono text-neutral-400">{t.zone}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mt-1.5">
            {fill(t.welcome, { name: user?.name || t.farmer })}
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            {fill(t.monitoring, { farm: primaryFarm })}
          </p>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleTriggerCycle}
            disabled={irrigationStatus === "cycling"}
            className="px-4 py-2.5 rounded-lg bg-[#c6f04a] hover:bg-[#b5e03b] active:scale-95 text-[#0d0f0c] text-sm font-semibold flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(198,240,74,0.3)] disabled:opacity-50"
          >
            {irrigationStatus === "cycling" ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-[#0d0f0c] border-t-transparent rounded-full animate-spin" />
                {t.cycling}
              </>
            ) : irrigationStatus === "completed" ? (
              <>
                <span>✓</span> {t.complete}
              </>
            ) : (
              <>
                <IconDrop /> {t.trigger}
              </>
            )}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Water Recovery */}
        <div className="p-5 rounded-xl bg-gradient-to-b from-[#0f2e18]/40 to-black/40 border border-[#c6f04a]/20 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-neutral-400 font-mono">
            <span>{t.kpi.recovery}</span>
            <span className="text-[#c6f04a]">{t.kpi.liveTag}</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">{lastWaterAmount}</span>
            <span className="text-xs text-neutral-400 font-mono">{t.kpi.liters}</span>
          </div>
          <div className="mt-3 text-xs text-emerald-400 flex items-center gap-1">
            <span>↑ +22%</span>
            <span className="text-neutral-400">{t.kpi.vsDrip}</span>
          </div>
        </div>

        {/* Card 2: Soil Moisture */}
        <div className="p-5 rounded-xl bg-white/[0.03] border border-white/10 backdrop-blur-sm">
          <div className="flex items-center justify-between text-xs text-neutral-400 font-mono">
            <span>{t.kpi.moisture}</span>
            <span className="text-emerald-400">{t.kpi.optimal}</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">41.8</span>
            <span className="text-xs text-neutral-400 font-mono">% VWC</span>
          </div>
          <div className="mt-3 text-xs text-neutral-400 flex items-center gap-1">
            <span>{t.kpi.target}</span>
          </div>
        </div>

        {/* Card 3: AI Crop Diagnostic */}
        <div className="p-5 rounded-xl bg-white/[0.03] border border-white/10 backdrop-blur-sm">
          <div className="flex items-center justify-between text-xs text-neutral-400 font-mono">
            <span>{t.kpi.health}</span>
            <span className="text-emerald-400">{t.kpi.clear}</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">98.2</span>
            <span className="text-xs text-neutral-400 font-mono">{t.kpi.index}</span>
          </div>
          <div className="mt-3 text-xs text-neutral-400">
            {t.kpi.alerts}
          </div>
        </div>

        {/* Card 4: Energy Subsystem */}
        <div className="p-5 rounded-xl bg-white/[0.03] border border-white/10 backdrop-blur-sm">
          <div className="flex items-center justify-between text-xs text-neutral-400 font-mono">
            <span>{t.kpi.solar}</span>
            <span className="text-yellow-400">13.8V</span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">3.4</span>
            <span className="text-xs text-neutral-400 font-mono">{t.kpi.perDay}</span>
          </div>
          <div className="mt-3 text-xs text-neutral-400">
            {t.kpi.reserve}
          </div>
        </div>
      </div>

      {/* Field Parcels & ROOTLOOP Subsystem Visual Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Parcels Status */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-white/[0.02] border border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">{t.parcels.title}</h2>
            <span className="text-xs font-mono text-neutral-400">{t.parcels.ingest}</span>
          </div>

          <div className="divide-y divide-white/5 text-sm">
            {/* Parcel A */}
            <div className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="font-medium text-white flex items-center gap-2">
                  {t.parcels.items[0].name}
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">
                    {t.parcels.items[0].status}
                  </span>
                </div>
                <div className="text-xs text-neutral-400 mt-1 font-mono">
                  {t.parcels.items[0].details}
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono">
                <div>
                  <span className="text-neutral-500">{t.parcels.moisture}</span> <span className="text-white">43%</span>
                </div>
                <div>
                  <span className="text-neutral-500">{t.parcels.temp}</span> <span className="text-white">22.4°C</span>
                </div>
                <div>
                  <span className="text-neutral-500">{t.parcels.flow}</span> <span className="text-[#c6f04a]">0.0 L/m</span>
                </div>
              </div>
            </div>

            {/* Parcel B */}
            <div className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="font-medium text-white flex items-center gap-2">
                  {t.parcels.items[1].name}
                  <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono">
                    {t.parcels.items[1].status}
                  </span>
                </div>
                <div className="text-xs text-neutral-400 mt-1 font-mono">
                  {t.parcels.items[1].details}
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono">
                <div>
                  <span className="text-neutral-500">{t.parcels.moisture}</span> <span className="text-white">39%</span>
                </div>
                <div>
                  <span className="text-neutral-500">{t.parcels.temp}</span> <span className="text-white">21.8°C</span>
                </div>
                <div>
                  <span className="text-neutral-500">{t.parcels.flow}</span> <span className="text-[#c6f04a]">1.4 L/m</span>
                </div>
              </div>
            </div>

            {/* Parcel C */}
            <div className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="font-medium text-white flex items-center gap-2">
                  {t.parcels.items[2].name}
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">
                    {t.parcels.items[2].status}
                  </span>
                </div>
                <div className="text-xs text-neutral-400 mt-1 font-mono">
                  {t.parcels.items[2].details}
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono">
                <div>
                  <span className="text-neutral-500">{t.parcels.moisture}</span> <span className="text-white">45%</span>
                </div>
                <div>
                  <span className="text-neutral-500">{t.parcels.temp}</span> <span className="text-white">24.1°C</span>
                </div>
                <div>
                  <span className="text-neutral-500">{t.parcels.flow}</span> <span className="text-[#c6f04a]">0.0 L/m</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: AI & ROOTLOOP Health Status */}
        <div className="p-6 rounded-xl bg-white/[0.02] border border-white/10 space-y-4">
          <h2 className="text-lg font-semibold text-white">{t.system.title}</h2>
          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between">
              <span className="text-neutral-400">FastAPI REST Backend</span>
              <span className="text-emerald-400">{t.system.connected} (8001)</span>
            </div>
            <div className="p-3 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between">
              <span className="text-neutral-400">PostgreSQL / TimescaleDB</span>
              <span className="text-emerald-400">{t.system.online} (5433)</span>
            </div>
            <div className="p-3 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between">
              <span className="text-neutral-400">Mosquitto MQTT Broker</span>
              <span className="text-emerald-400">{t.system.tls} (8883)</span>
            </div>
            <div className="p-3 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between">
              <span className="text-neutral-400">Celery + Redis Queue</span>
              <span className="text-emerald-400">{t.system.ready}</span>
            </div>
            <div className="p-3 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between">
              <span className="text-neutral-400">AI Vision Engine (ONNX)</span>
              <span className="text-[#c6f04a]">{t.system.active} (v1.0)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
