"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import type { Locale } from "@/i18n/config";
import { parsePlan, savePlan } from "@/lib/farmPlan";
import { parsePlace, savePlace } from "@/lib/place";
import { PlanSummary } from "./PlanSummary";
import { HeaderPills } from "./farmHeader";

/** Where the MIZU KIZUNA crop planner (mizu-kizuna/, its own FastAPI server) runs. */
const MIZU_URL = (process.env.NEXT_PUBLIC_MIZU_URL || "http://localhost:8010").replace(/\/$/, "");
const MIZU_ORIGIN = new URL(MIZU_URL).origin;

// MIZU KIZUNA speaks French, Tunisian (tn) and Japanese; English falls back to French.
const MIZU_LANG: Record<Locale, "fr" | "tn" | "ja"> = { fr: "fr", ar: "tn", ja: "ja", en: "fr" };

// Version of the planner's page (mizu-kizuna/static/index.html asset versions). Part of the frame address,
// so browsers fetch the new planner page instead of an old cached copy after an update.
const MIZU_UI_VERSION = "2.8";

type Status = "checking" | "online" | "offline";

export function CropPlanner() {
  const { m, locale } = useI18n();
  const t = m.planning;
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [status, setStatus] = useState<Status>("checking");
  const [tab, setTab] = useState<string>("farm");
  // The frame address is fixed at first render; later language changes are sent as messages, so the
  // farmer's drawn parcel and answers survive a language switch.
  const [src] = useState(() => `${MIZU_URL}/?embed=1&lang=${MIZU_LANG[locale]}&v=${MIZU_UI_VERSION}`);

  const check = useCallback(async () => {
    setStatus("checking");
    try {
      const res = await fetch(`${MIZU_URL}/api/health`, { cache: "no-store" });
      setStatus(res.ok ? "online" : "offline");
    } catch {
      setStatus("offline");
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  useEffect(() => {
    frameRef.current?.contentWindow?.postMessage({ type: "mizu:lang", lang: MIZU_LANG[locale] }, MIZU_ORIGIN);
  }, [locale]);

  // "Valider ce plan" in the planner sends the plan here; Irrigation 3D and Post-Harvest then reuse it.
  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (e.origin !== MIZU_ORIGIN || e.source !== frameRef.current?.contentWindow) return;
      const data = e.data as { type?: unknown; plan?: unknown; place?: unknown } | null;
      // The place searched or located in the planner becomes the farm's place on every page.
      if (data?.type === "mizu:place") {
        const place = parsePlace(data.place, "selected");
        if (place) savePlace(place);
        return;
      }
      if (data?.type !== "mizu:plan") return;
      const plan = parsePlan(data.plan);
      if (plan) savePlan(plan);
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  // Tabs scroll the planner to the matching part (presentation only; nothing is recomputed).
  const TABS = [
    { view: "farm", label: t.tabFarm, icon: <IconFarm /> },
    { view: "reco", label: t.tabReco, icon: <IconSparkles /> },
    { view: "compare", label: t.tabCompare, icon: <IconBars /> },
    { view: "details", label: t.tabDetails, icon: <IconCoins /> },
  ] as const;
  const showView = (view: string) => {
    setTab(view);
    frameRef.current?.contentWindow?.postMessage({ type: "mizu:view", view }, MIZU_ORIGIN);
  };

  return (
    <div className="flex flex-col h-[calc(100svh-65px)] lg:h-svh bg-gradient-to-b from-[#0f2d18] to-[#0b2212]">
      <header className="px-5 sm:px-6 pt-5 pb-3 flex flex-col gap-4">
        <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <span className="text-[40px] leading-none"><LeafIcon /></span>
            <div className="min-w-0">
              <h1 className="text-2xl sm:text-[32px] font-extrabold text-white tracking-tight leading-tight">{t.title}</h1>
              <p className="text-sm sm:text-base text-[#d6e6cf] mt-0.5">{t.lead}</p>
              {locale === "en" && <p className="text-xs text-[#c6f04a] mt-1.5">{t.noEnglish}</p>}
            </div>
          </div>
          <HeaderPills />
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          {TABS.map((x) => (
            <button
              key={x.view}
              type="button"
              onClick={() => showView(x.view)}
              aria-pressed={tab === x.view}
              className={`inline-flex items-center gap-2.5 rounded-2xl px-5 py-2.5 text-[15px] font-semibold transition-colors ${
                tab === x.view
                  ? "bg-gradient-to-r from-[#c8f56a] to-[#8fdc4e] text-[#0c2410] shadow-[0_8px_22px_rgba(143,220,78,0.35)]"
                  : "bg-[#173a1f]/80 text-white border border-white/10 hover:bg-[#1d4826]"
              }`}
            >
              <span className="text-lg">{x.icon}</span>
              {x.label}
            </button>
          ))}
          <span className="ms-auto flex items-center gap-4">
            <PlanSummary variant="planner" />
            <a
              href={src.replace("embed=1&", "").replace(/&v=[^&]*/, "")}
              target="_blank"
              rel="noreferrer"
              className="shrink-0 py-2 text-xs text-[#cfe0c7] hover:text-white underline underline-offset-4"
            >
              {t.openTab}
            </a>
          </span>
        </div>
      </header>

      <div className="relative flex-1 min-h-[520px]">
        {status === "offline" ? (
          <div className="absolute inset-0 grid place-items-center p-6">
            <div role="alert" className="max-w-lg w-full rounded-xl border border-white/10 bg-white/[0.03] p-6 space-y-3">
              <h2 className="text-lg font-semibold text-white">{t.offlineTitle}</h2>
              <p className="text-sm text-neutral-400">{t.offlineText}</p>
              <pre dir="ltr" className="text-xs text-[#c6f04a] bg-black/40 border border-white/10 rounded-lg p-3 overflow-x-auto">
                cd mizu-kizuna && .venv/bin/python -m uvicorn main:app --port 8010
              </pre>
              <button
                type="button"
                onClick={() => void check()}
                className="px-4 py-2 rounded-lg bg-[#c6f04a] hover:bg-[#b5e03b] text-[#0d0f0c] text-sm font-semibold"
              >
                {t.retry}
              </button>
            </div>
          </div>
        ) : (
          <iframe
            ref={frameRef}
            src={src}
            title={t.frameTitle}
            className="absolute inset-0 w-full h-full border-0"
            allow="geolocation"
            onLoad={() => frameRef.current?.contentWindow?.postMessage({ type: "mizu:lang", lang: MIZU_LANG[locale] }, MIZU_ORIGIN)}
          />
        )}
      </div>
    </div>
  );
}

const icon = (d: string) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
);
const IconFarm = () => icon("M3 21h18M5 21V10l7-5 7 5v11M9 21v-6h6v6M3 10l9-7 9 7");
const IconSparkles = () => icon("M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3Zm7 11 .8 2.2 2.2.8-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14Z");
const IconBars = () => icon("M4 20V10M10 20V4M16 20v-7M22 20H2");
const IconCoins = () => icon("M12 4c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3ZM4 7v5c0 1.7 3.6 3 8 3s8-1.3 8-3V7M4 12v5c0 1.7 3.6 3 8 3s8-1.3 8-3v-5");

function LeafIcon() {
  return (
    <svg viewBox="0 0 48 48" width="1em" height="1em" aria-hidden="true">
      <defs>
        <linearGradient id="fl-plan-leaf" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="#2f8f2a" />
          <stop offset="1" stopColor="#8fdc4e" />
        </linearGradient>
      </defs>
      <path d="M8 40C8 20 20 8 42 6c-1 22-13 34-32 34Z" fill="url(#fl-plan-leaf)" />
      <path d="M10 38C18 28 26 20 36 13" stroke="#0f3a16" strokeWidth="2" strokeLinecap="round" fill="none" opacity=".55" />
    </svg>
  );
}
