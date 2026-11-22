"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import type { Locale } from "@/i18n/config";

/** Where the MIZU KIZUNA crop planner (mizu-kizuna/, its own FastAPI server) runs. */
const MIZU_URL = (process.env.NEXT_PUBLIC_MIZU_URL || "http://localhost:8010").replace(/\/$/, "");
const MIZU_ORIGIN = new URL(MIZU_URL).origin;

// MIZU KIZUNA speaks French, Tunisian (tn) and Japanese; English falls back to French.
const MIZU_LANG: Record<Locale, "fr" | "tn" | "ja"> = { fr: "fr", ar: "tn", ja: "ja", en: "fr" };

type Status = "checking" | "online" | "offline";

export function CropPlanner() {
  const { m, locale } = useI18n();
  const t = m.planning;
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [status, setStatus] = useState<Status>("checking");
  // The frame address is fixed at first render; later language changes are sent as messages, so the
  // farmer's drawn parcel and answers survive a language switch.
  const [src] = useState(() => `${MIZU_URL}/?embed=1&lang=${MIZU_LANG[locale]}`);

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

  return (
    <div className="flex flex-col h-[calc(100svh-65px)] lg:h-svh">
      <header className="px-6 sm:px-10 pt-6 pb-4 border-b border-white/10 flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div className="max-w-3xl">
          <h1 className="text-2xl font-bold text-white tracking-tight">{t.title}</h1>
          <p className="text-sm text-neutral-400 mt-1">{t.subtitle}</p>
          {locale === "en" && <p className="text-xs text-[#c6f04a] mt-1.5">{t.noEnglish}</p>}
        </div>
        <a
          href={src.replace("embed=1&", "")}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 self-start md:self-auto py-2 text-xs text-neutral-300 hover:text-white underline underline-offset-4"
        >
          {t.openTab}
        </a>
      </header>

      <div className="relative flex-1 min-h-[520px] bg-[#0d100d]">
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
