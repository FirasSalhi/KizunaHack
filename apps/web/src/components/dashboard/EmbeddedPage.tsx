"use client";

import React from "react";
import { useI18n } from "@/i18n/I18nProvider";

type Props = {
  /** Accessible name of the frame. */
  frameTitle: string;
  /** Address of the page, served by app/embed/[page]/route.ts. */
  src: string;
  /** Background behind the frame while the page loads, matching the page's own. */
  background: string;
};

/**
 * A dashboard section that shows a standalone page in a frame, filling the section. The page is served in the
 * dashboard's language (?lang=); changing the language reloads it.
 */
export function EmbeddedPage({ frameTitle, src, background }: Props) {
  const { locale } = useI18n();
  const url = `${src}?lang=${locale}`;
  return (
    <div className="relative h-[calc(100svh-65px)] lg:h-svh min-h-[520px]" style={{ background }}>
      <iframe key={url} src={url} title={frameTitle} className="absolute inset-0 w-full h-full border-0" allow="geolocation" />
    </div>
  );
}
