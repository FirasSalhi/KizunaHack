import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

export default function config(phase: string): NextConfig {
  return {
    reactStrictMode: true,
    outputFileTracingRoot: fileURLToPath(new URL("../..", import.meta.url)),
    // The dev server writes to its own folder, so a `next build` running at the same time
    // cannot overwrite the files it is serving (that broke every page with a 500).
    distDir: phase === PHASE_DEVELOPMENT_SERVER ? ".next-dev" : ".next",
  };
}
