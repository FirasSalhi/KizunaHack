"use client";

import React, { useEffect, useRef, useState } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { IconClose } from "@/components/icons";
import { useI18n } from "@/i18n/I18nProvider";
import { useInstall } from "./useInstall";

const DISMISS_KEY = "fl_install_dismissed_at";
const DISMISS_DAYS = 14;

/** "Install the app" button for the landing page's top bar. Hidden when there is nothing to install. */
export function InstallButton({ className = "" }: { className?: string }) {
  const { m } = useI18n();
  const { mode, install } = useInstall();
  const [iosOpen, setIosOpen] = useState(false);
  if (mode === "none") return null;
  return (
    <>
      <button
        type="button"
        onClick={() => (mode === "prompt" ? void install() : setIosOpen(true))}
        className={className}
        aria-label={m.pwa.install}
      >
        <IconDownload />
        <span className="install-label">{m.pwa.install}</span>
      </button>
      {iosOpen && <IosSheet onClose={() => setIosOpen(false)} />}
    </>
  );
}

/** Bottom banner on phones inviting to install, until installed or dismissed (asked again after 14 days). */
export function InstallBanner() {
  const { m } = useI18n();
  const t = m.pwa;
  const { mode, install } = useInstall();
  const [visible, setVisible] = useState(false);
  const [iosOpen, setIosOpen] = useState(false);

  useEffect(() => {
    if (mode === "none") {
      setVisible(false);
      return;
    }
    let dismissedAt = 0;
    try {
      dismissedAt = Number(localStorage.getItem(DISMISS_KEY) || 0);
    } catch {
      // storage blocked: just show it
    }
    if (Date.now() - dismissedAt < DISMISS_DAYS * 864e5) return;
    const timer = setTimeout(() => setVisible(true), 2500); // let the page settle first
    return () => clearTimeout(timer);
  }, [mode]);

  function dismiss() {
    setVisible(false);
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      // storage blocked: hidden for this visit only
    }
  }

  if (!visible) return iosOpen ? <IosSheet onClose={() => setIosOpen(false)} /> : null;
  return (
    <>
      <div
        role="region"
        aria-label={t.installTitle}
        className="lg:hidden fixed inset-x-3 bottom-3 z-[60] rounded-2xl border border-white/10 bg-[#121612]/95 backdrop-blur p-3 shadow-[0_10px_30px_rgba(0,0,0,0.5)] flex items-center gap-3"
        style={{ marginBottom: "env(safe-area-inset-bottom)" }}
      >
        <BrandLogo size={44} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white">{t.installTitle}</p>
          <p className="text-xs text-neutral-400">{t.installText}</p>
        </div>
        <button
          type="button"
          onClick={async () => {
            if (mode === "prompt") {
              if (await install()) setVisible(false);
            } else {
              setVisible(false);
              setIosOpen(true);
            }
          }}
          className="px-3 py-2 rounded-lg bg-[#c6f04a] hover:bg-[#b5e03b] text-[#0d0f0c] text-sm font-semibold shrink-0"
        >
          {t.install}
        </button>
        <button type="button" onClick={dismiss} aria-label={t.notNow} className="p-1 text-neutral-500 hover:text-white shrink-0">
          <IconClose />
        </button>
      </div>
    </>
  );
}

/** iPhone / iPad: Safari has no install button, so show the three taps instead. */
function IosSheet({ onClose }: { onClose: () => void }) {
  const { m } = useI18n();
  const t = m.pwa;
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[70] flex items-end sm:items-center justify-center p-3">
      <button type="button" tabIndex={-1} aria-hidden="true" onClick={onClose} className="absolute inset-0 bg-black/60 cursor-default" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="ios-install-title"
        className="relative w-full max-w-sm rounded-2xl border border-white/10 bg-[#121612] p-5 space-y-4"
        style={{ marginBottom: "env(safe-area-inset-bottom)" }}
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="ios-install-title" className="text-lg font-semibold text-white">{t.iosTitle}</h2>
          <button ref={closeRef} type="button" onClick={onClose} aria-label={t.close} className="p-1 text-neutral-400 hover:text-white">
            <IconClose />
          </button>
        </div>
        <ol className="space-y-3 text-sm text-neutral-200">
          <Step n={1}>
            {t.iosStep1} <IconShare className="inline text-[#5aa9ff] align-[-3px]" />
          </Step>
          <Step n={2}>{t.iosStep2}</Step>
          <Step n={3}>{t.iosStep3}</Step>
        </ol>
        <p className="text-xs text-neutral-500">{t.iosNote}</p>
      </div>
    </div>
  );
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <li className="flex gap-3 items-start">
      <span className="shrink-0 w-6 h-6 rounded-full bg-[#c6f04a]/15 text-[#c6f04a] text-xs font-bold grid place-items-center">{n}</span>
      <span className="pt-0.5">{children}</span>
    </li>
  );
}

function IconDownload() {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 4v11M7 10l5 5 5-5M5 20h14" />
    </svg>
  );
}

/** Safari's Share symbol (square with an up arrow), so the farmer recognises the button. */
function IconShare({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" width="1.15em" height="1.15em" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className={className}>
      <path d="M12 3v12M8 7l4-4 4 4" />
      <path d="M7 11H5v10h14V11h-2" />
    </svg>
  );
}
