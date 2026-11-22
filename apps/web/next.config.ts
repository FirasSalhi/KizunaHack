import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import withSerwistInit from "@serwist/next";
import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

export default function config(phase: string): NextConfig {
  const dev = phase === PHASE_DEVELOPMENT_SERVER;
  // Installable PWA: the service worker (src/app/sw.ts) is built to public/sw.js. It stays off in
  // development so it never serves stale code while you edit.
  const withSerwist = withSerwistInit({
    swSrc: "src/app/sw.ts",
    swDest: "public/sw.js",
    disable: dev,
    // The offline screen is rendered per request, so it is cached explicitly, once per build.
    additionalPrecacheEntries: [{ url: "/~offline", revision: randomUUID() }],
  });
  return withSerwist({
    reactStrictMode: true,
    outputFileTracingRoot: fileURLToPath(new URL("../..", import.meta.url)),
    // The dev server writes to its own folder, so a `next build` running at the same time
    // cannot overwrite the files it is serving (that broke every page with a 500).
    distDir: dev ? ".next-dev" : ".next",
    // Put the metadata (manifest link, theme colour, Apple home-screen tags) in <head> for every
    // browser. Next otherwise streams it into <body> on dynamic pages, where Chrome and iOS Safari
    // don't look, so the app wasn't installable. Our metadata is static: no cost to blocking on it.
    htmlLimitedBots: /.*/,
  });
}
