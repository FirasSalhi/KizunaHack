"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { IconScanLeaf } from "@/components/icons";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n/I18nProvider";
import { ApiError } from "@/services/apiClient";
import { plantService } from "@/services/plantService";
import type { ScanResult, ScannerStatus } from "@/types/plants";
import { ScanResultView } from "./ScanResultView";
import { ScanHistory } from "./ScanHistory";

const DEMO_TOKEN = "demo_access_token_jwt";
const LIME = "bg-[#c6f04a] hover:bg-[#b5e03b] text-[#0d0f0c]";

type Phase = "idle" | "analysing" | "done" | "error";

/** Plant scanner (ported from is9ini): photo -> plant, health, care sheet; history for signed-in users. */
export function PlantScanner() {
  const { m, locale } = useI18n();
  const t = m.scanner;
  const { token } = useAuth();
  const signedIn = !!token && token !== DEMO_TOKEN;

  const [status, setStatus] = useState<ScannerStatus | null | "offline">(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [dragging, setDragging] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await plantService.status());
    } catch {
      setStatus("offline");
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  // Free the previous preview's object URL.
  useEffect(() => () => {
    if (preview?.startsWith("blob:")) URL.revokeObjectURL(preview);
  }, [preview]);

  async function scan(file: File) {
    if (!file.type.startsWith("image/")) {
      setError(t.errBadPhoto);
      setPhase("error");
      return;
    }
    setPreview(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setPhase("analysing");
    try {
      const res = await plantService.identify(file);
      setResult(res);
      setPhase("done");
      if (res.saved) setHistoryKey((k) => k + 1);
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "";
      setError(
        code === "PHOTO_TOO_LARGE" ? t.errTooLarge
          : code === "BAD_PHOTO" ? t.errBadPhoto
          : code === "SCANNER_NOT_INSTALLED" ? t.notInstalled
          : code === "NETWORK_ERROR" ? t.offline
          : t.errGeneric,
      );
      setPhase("error");
    }
  }

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) void scan(file);
  }

  function reset() {
    setPreview(null);
    setResult(null);
    setError(null);
    setPhase("idle");
  }

  async function openScan(id: string) {
    try {
      const scan = await plantService.getScan(id);
      setResult({ ...scan.result, saved: true, scan_id: id });
      setPreview(await plantService.photoUrl(id, "full"));
      setError(null);
      setPhase("done");
    } catch {
      setError(t.errGeneric);
      setPhase("error");
    }
  }

  const engines = status && status !== "offline" ? status.engines : null;
  const busy = phase === "analysing";

  return (
    <div className="flex flex-col min-h-[calc(100svh-65px)] lg:min-h-svh">
      <header className="px-6 sm:px-10 pt-6 pb-4 border-b border-white/10">
        <h1 className="text-2xl font-bold text-white tracking-tight">{t.title}</h1>
        <p className="text-sm text-neutral-400 mt-1 max-w-3xl">{t.subtitle}</p>
        {locale !== "en" && <p className="text-xs text-[#c6f04a] mt-1.5">{t.resultsInEnglish}</p>}
      </header>

      <div className="flex-1 grid xl:grid-cols-[minmax(320px,400px)_1fr] gap-6 p-6 sm:p-10">
        {/* Left: photo, engines, history */}
        <div className="space-y-5 min-w-0">
          {status === "offline" && (
            <div role="alert" className="rounded-xl border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-200 space-y-2">
              <p>{t.offline}</p>
              <button type="button" onClick={() => void loadStatus()} className="text-xs underline underline-offset-4">
                {t.retry}
              </button>
            </div>
          )}
          {status && status !== "offline" && !status.installed && (
            <div role="alert" className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100 space-y-2">
              <p>{t.notInstalled}</p>
              <pre dir="ltr" className="text-xs text-[#c6f04a] bg-black/40 rounded-lg p-2 overflow-x-auto">
                cd services/api && uv run python -m app.plants.catalog
              </pre>
            </div>
          )}

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              const file = e.dataTransfer.files?.[0];
              if (file && !busy) void scan(file);
            }}
            className={`rounded-2xl border ${dragging ? "border-[#c6f04a] bg-[#c6f04a]/5" : "border-white/10 bg-white/[0.03]"} overflow-hidden transition-colors`}
          >
            {preview ? (
              <div className="relative aspect-[4/3] bg-black">
                {/* eslint-disable-next-line @next/next/no-img-element -- local object URL */}
                <img src={preview} alt={t.photoAlt} className="absolute inset-0 w-full h-full object-cover" />
                {busy && (
                  <div className="absolute inset-0 grid place-items-center bg-black/55 backdrop-blur-[2px]" aria-live="polite">
                    <div className="flex items-center gap-3 rounded-full bg-black/70 border border-white/10 px-4 py-2">
                      <span className="w-4 h-4 border-2 border-[#c6f04a] border-t-transparent rounded-full animate-spin" />
                      <span className="text-sm font-medium text-white">{t.analysing}</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="px-6 py-10 text-center">
                <div className="mx-auto mb-4 grid place-items-center w-16 h-16 rounded-2xl bg-[#c6f04a]/10 text-[#c6f04a] text-3xl">
                  <IconScanLeaf />
                </div>
                <p className="font-semibold text-white">{t.pointCamera}</p>
                <p className="text-sm text-neutral-400 mt-1">{t.pointHint}</p>
                <p className="text-xs text-neutral-500 mt-3">{t.dropHint}</p>
              </div>
            )}

            <div className="p-4 border-t border-white/10 space-y-3">
              {phase === "error" && error && <p role="alert" className="text-sm text-red-300">{error}</p>}
              {phase === "done" && result && (
                <p className={`text-xs ${result.saved ? "text-[#c6f04a]" : "text-neutral-400"}`}>
                  {result.saved ? t.saved : t.notSaved}
                </p>
              )}
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => cameraRef.current?.click()}
                  className={`px-4 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-50 ${LIME}`}
                >
                  {preview ? t.scanAgain : t.takePhoto}
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => galleryRef.current?.click()}
                  className="px-4 py-2.5 rounded-lg text-sm font-semibold border border-white/15 text-white hover:border-[#c6f04a] hover:text-[#c6f04a] disabled:opacity-50"
                >
                  {t.gallery}
                </button>
              </div>
              {preview && !busy && (
                <button type="button" onClick={reset} className="w-full text-xs text-neutral-400 hover:text-white">
                  {t.clear}
                </button>
              )}
              <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden onChange={onPick} />
              <input ref={galleryRef} type="file" accept="image/*" hidden onChange={onPick} />
            </div>
          </div>

          {engines && (
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-2">
              <p className="text-xs font-mono uppercase tracking-wider text-neutral-500">{t.engines}</p>
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    ["plantnet", "Pl@ntNet"],
                    ["bioclip", "BioCLIP 2"],
                    ["verdant", "verdant"],
                  ] as const
                ).map(([key, label]) => (
                  <span
                    key={key}
                    className={`text-xs px-2.5 py-1 rounded-full border ${engines[key] ? "border-[#c6f04a]/40 text-[#c6f04a] bg-[#c6f04a]/10" : "border-white/10 text-neutral-500"}`}
                  >
                    {engines[key] ? "● " : "○ "}
                    {label}
                  </span>
                ))}
              </div>
              {!engines.plantnet && <p className="text-xs text-neutral-500">{t.plantnetOff}</p>}
            </div>
          )}

          {signedIn ? (
            <ScanHistory refreshKey={historyKey} activeId={result?.scan_id} onOpen={(id) => void openScan(id)} onDeleted={(id) => {
              if (result?.scan_id === id) reset();
            }} />
          ) : (
            <p className="text-xs text-neutral-500 rounded-xl border border-white/10 p-4">{t.historySignIn}</p>
          )}
        </div>

        {/* Right: the result */}
        <div className="min-w-0">
          {result ? (
            <ScanResultView
              result={result}
              onChange={(next) => {
                setResult(next);
                if (next.saved) setHistoryKey((k) => k + 1);
              }}
            />
          ) : (
            <div className="h-full min-h-[280px] rounded-2xl border border-dashed border-white/10 grid place-items-center p-8 text-center">
              <p className="text-sm text-neutral-500 max-w-sm">{busy ? t.analysing : t.emptyResult}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
