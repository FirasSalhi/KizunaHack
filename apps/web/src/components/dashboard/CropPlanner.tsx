"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import type { Locale } from "@/i18n/config";
import { parsePlan, savePlan } from "@/lib/farmPlan";
import { parsePlace, savePlace } from "@/lib/place";

/** Where the MIZU KIZUNA crop planner (mizu-kizuna/, its own FastAPI server) runs. */
const MIZU_URL = (process.env.NEXT_PUBLIC_MIZU_URL || "http://localhost:8010").replace(/\/$/, "");
const MIZU_ORIGIN = new URL(MIZU_URL).origin;

// MIZU KIZUNA speaks French, Tunisian (tn) and Japanese; English falls back to French.
const MIZU_LANG: Record<Locale, "fr" | "tn" | "ja"> = { fr: "fr", ar: "tn", ja: "ja", en: "fr" };

// Version of the planner's page (mizu-kizuna/static/index.html asset versions). Part of the frame address,
// so browsers fetch the new planner page instead of an old cached copy after an update.
const MIZU_UI_VERSION = "2.9";

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
    <div className="flex flex-col h-[calc(100svh-65px)] lg:h-svh bg-gradient-to-b from-[#0d0f0c] to-[#020302]">
      {/* View tabs: scroll the planner to the matching part */}
      <nav className="px-5 sm:px-6 pt-4 pb-3 flex flex-wrap items-center gap-2.5" aria-label={t.title}>
      {TABS.map((x) => (
        <button
          key={x.view}
          type="button"
          onClick={() => showView(x.view)}
          aria-pressed={tab === x.view}
          className={`inline-flex items-center gap-2.5 rounded-2xl px-5 py-2.5 text-[15px] font-semibold transition-colors ${
            tab === x.view
              ? "bg-gradient-to-r from-[#c6f04a] to-[#b5e03b] text-[#0d0f0c] shadow-[0_8px_22px_rgba(198,240,74,0.25)]"
              : "bg-white/[0.06] text-white border border-white/10 hover:bg-white/[0.1]"
          }`}
        >
          <span className="text-lg">{x.icon}</span>
          {x.label}
        </button>
      ))}
      </nav>

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
