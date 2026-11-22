"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

/** Chrome / Edge / Samsung Internet event that lets the page show the browser's install dialog. */
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

// The event can fire before React has mounted anything, so it is caught at module level.
let deferred: BeforeInstallPromptEvent | null = null;
let installed = false;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault(); // keep it for our own "Install" button
    deferred = e as BeforeInstallPromptEvent;
    notify();
  });
  window.addEventListener("appinstalled", () => {
    deferred = null;
    installed = true;
    notify();
  });
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Running as the installed app (home screen), not in a browser tab. */
function isStandalone(): boolean {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches === true ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

/** iPhone / iPad Safari: no install prompt; the user adds the app from the Share menu. */
function isIos(): boolean {
  const ua = navigator.userAgent;
  const iPadOs = navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
  return /iPhone|iPad|iPod/.test(ua) || iPadOs;
}

export type InstallMode = "prompt" | "ios" | "none";

/** How this browser can install FARMLINK right now, and a function to start it. */
export function useInstall() {
  const canPrompt = useSyncExternalStore(subscribe, () => deferred !== null, () => false);
  const justInstalled = useSyncExternalStore(subscribe, () => installed, () => false);
  const [env, setEnv] = useState<{ standalone: boolean; ios: boolean } | null>(null);

  useEffect(() => {
    setEnv({ standalone: isStandalone(), ios: isIos() });
  }, []);

  let mode: InstallMode = "none";
  if (env && !env.standalone && !justInstalled) {
    if (canPrompt) mode = "prompt";
    else if (env.ios) mode = "ios";
  }

  async function install(): Promise<boolean> {
    const event = deferred;
    if (!event) return false;
    await event.prompt();
    const { outcome } = await event.userChoice;
    deferred = null; // a prompt can only be used once
    notify();
    return outcome === "accepted";
  }

  return { mode, install };
}
