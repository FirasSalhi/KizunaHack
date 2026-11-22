"use client";

import React from "react";

type Props = {
  title: string;
  subtitle: string;
  /** Shown in lime under the subtitle, e.g. which language the embedded page is in. */
  note?: string;
  openTab: string;
  frameTitle: string;
  /** Address of the page, served by app/embed/[page]/route.ts. */
  src: string;
  /** Background behind the frame while the page loads, matching the page's own. */
  background: string;
};

/** A dashboard section that shows a standalone page unchanged in a frame, under a FARMLINK header. */
export function EmbeddedPage({ title, subtitle, note, openTab, frameTitle, src, background }: Props) {
  return (
    <div className="flex flex-col h-[calc(100svh-65px)] lg:h-svh">
      <header className="px-6 sm:px-10 pt-6 pb-4 border-b border-white/10 flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div className="max-w-3xl">
          <h1 className="text-2xl font-bold text-white tracking-tight">{title}</h1>
          <p className="text-sm text-neutral-400 mt-1">{subtitle}</p>
          {note && <p className="text-xs text-[#c6f04a] mt-1.5">{note}</p>}
        </div>
        <a
          href={src}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 self-start md:self-auto py-2 text-xs text-neutral-300 hover:text-white underline underline-offset-4"
        >
          {openTab}
        </a>
      </header>

      <div className="relative flex-1 min-h-[520px]" style={{ background }}>
        <iframe src={src} title={frameTitle} className="absolute inset-0 w-full h-full border-0" allow="geolocation" />
      </div>
    </div>
  );
}
