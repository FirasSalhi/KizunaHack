import React from "react";

/** The Mdhalla (مظلّة) logo: a straw sunshade over a date palm, on a white rounded tile. */
export function BrandLogo({ size = 40, className = "" }: { size?: number; className?: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src="/brand/mdhalla-logo.png" alt="" width={size} height={size} className={`block rounded-xl bg-white shrink-0 ${className}`} />
  );
}
