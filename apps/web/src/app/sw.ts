/// <reference lib="webworker" />
// FARMLINK service worker (Serwist): app shell and static files cached for fast start and offline use.
import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { NetworkOnly, Serwist } from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    // API calls (FARMLINK, crop planner) always go to the network: account data is never stored in the
    // browser cache, where another person using the same phone could see it.
    { matcher: ({ url }) => url.pathname.startsWith("/api/"), handler: new NetworkOnly() },
    ...defaultCache,
  ],
  fallbacks: {
    // A page that can't load while offline shows the offline screen instead of the browser's error.
    entries: [{ url: "/~offline", matcher: ({ request }) => request.destination === "document" }],
  },
});

serwist.addEventListeners();
