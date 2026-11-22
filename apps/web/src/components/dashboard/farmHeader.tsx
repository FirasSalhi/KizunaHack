"use client";

import React, { useEffect, useState } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { PLAN_EVENT, loadPlan, type FarmPlan } from "@/lib/farmPlan";
import { placeLabel, usePlace } from "@/lib/place";
import { apiClient } from "@/services/apiClient";

/** The validated crop plan, kept in sync with Crop Planning. */
export function usePlan() {
  const [plan, setPlan] = useState<FarmPlan | null>(null);
  useEffect(() => {
    const read = () => setPlan(loadPlan());
    read();
    window.addEventListener(PLAN_EVENT, read);
    window.addEventListener("storage", read);
    return () => {
      window.removeEventListener(PLAN_EVENT, read);
      window.removeEventListener("storage", read);
    };
  }, []);
  return plan;
}

export type WeatherNow = { temperature_c: number | null; humidity_pct: number | null; wind_kmh: number | null; condition: string };

/** Current weather at a point through the FARMLINK API (GET /api/v1/weather), refreshed every 15 minutes. */
export function useWeatherNow(lat: number | null, lon: number | null) {
  const [now, setNow] = useState<WeatherNow | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (lat == null || lon == null) return;
    let alive = true;
    const load = async () => {
      try {
        const data = await apiClient<{ current: WeatherNow }>(`/weather?lat=${lat}&lon=${lon}`);
        if (alive) {
          setNow(data.current);
          setFailed(false);
        }
      } catch {
        if (alive) setFailed(true);
      }
    };
    void load();
    const timer = setInterval(load, 15 * 60 * 1000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [lat, lon]);
  return { now, failed };
}

/** Weather, place and date pills of the dashboard page headers (live values only). */
export function HeaderPills() {
  const { m, locale } = useI18n();
  const t = m.home;
  const { place, status, locate } = usePlace();
  const { now, failed } = useWeatherNow(place?.lat ?? null, place?.lon ?? null);
  const nf = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const today = new Intl.DateTimeFormat(locale, { weekday: "short", day: "numeric", month: "short", year: "numeric" }).format(new Date());
  const pill = "flex items-center gap-3 rounded-2xl bg-[#173a1f]/80 border border-white/15 px-4 py-2.5 text-white shadow-lg";
  return (
    <div className="flex flex-wrap gap-3">
      {place && (
        <div className={pill}>
          {now ? (
            <>
              <WeatherIcon cond={now.condition} size={34} />
              <div className="leading-tight">
                <div className="text-xl font-bold tabular-nums">{now.temperature_c == null ? "—" : nf.format(now.temperature_c)}°C</div>
                <div className="text-xs text-white/85">{(t.wx as Record<string, string>)[now.condition] ?? ""}</div>
              </div>
            </>
          ) : (
            <span className="text-sm text-white/80">{failed ? t.weatherDown : t.computing}</span>
          )}
        </div>
      )}
      {place ? (
        <div className={pill}>
          <span className="text-xl text-[#a6e86b]"><IconPin /></span>
          <span className="text-[15px] font-medium">{placeLabel(place, (town) => t.placeNear.replace("{town}", town))}</span>
        </div>
      ) : (
        <button type="button" onClick={locate} className={`${pill} hover:bg-[#1d4826]`} title={t.placeUnknown}>
          <span className="text-xl text-[#a6e86b]"><IconPin /></span>
          <span className="text-[15px] font-medium">{status === "locating" ? t.placeLocating : t.locateMe}</span>
        </button>
      )}
      <div className={pill}>
        <span className="text-xl text-[#ffd54a]"><IconCalendar /></span>
        <span className="text-[15px] font-medium capitalize">{today}</span>
      </div>
    </div>
  );
}

const line = (d: string) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
);
const IconPin = () => line("M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Zm0-9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z");
const IconCalendar = () => line("M4 6h16v14H4V6Zm0 4h16M8 3v4m8-4v4M8 14h2m4 0h2");

/** Weather pictogram for the API's condition words (clear, partly, cloudy, fog, drizzle, rain, snow, storm). */
export function WeatherIcon({ cond, size }: { cond: string; size: number }) {
  const sun = (
    <g>
      <circle cx="12" cy="12" r="4.4" fill="#FFC83D" />
      <g stroke="#FFC83D" strokeWidth="1.8" strokeLinecap="round">
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <line key={a} x1="12" y1="2.6" x2="12" y2="4.8" transform={`rotate(${a} 12 12)`} />
        ))}
      </g>
    </g>
  );
  const cloud = (dx = 0, dy = 0, c = "#b9c6d3") => (
    <path transform={`translate(${dx} ${dy})`} d="M7 18h10a3.5 3.5 0 0 0 .3-7A5 5 0 0 0 7.6 10 4 4 0 0 0 7 18Z" fill={c} />
  );
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      {cond === "clear" && sun}
      {cond === "partly" && (
        <>
          <g transform="translate(-3 -3) scale(.85)">{sun}</g>
          {cloud(2, 2)}
        </>
      )}
      {(cond === "cloudy" || cond === "fog" || cond === "unknown") && cloud()}
      {(cond === "drizzle" || cond === "rain") && (
        <>
          {cloud(0, -2)}
          <g stroke="#3b8fe0" strokeWidth="1.6" strokeLinecap="round">
            <line x1="9" y1="18" x2="8" y2="21" />
            <line x1="13" y1="18" x2="12" y2="21" />
            <line x1="17" y1="18" x2="16" y2="21" />
          </g>
        </>
      )}
      {cond === "snow" && (
        <>
          {cloud(0, -2)}
          <g fill="#9fb3c8">
            <circle cx="9" cy="20" r="1" />
            <circle cx="13" cy="21" r="1" />
            <circle cx="16" cy="19.5" r="1" />
          </g>
        </>
      )}
      {cond === "storm" && (
        <>
          {cloud(0, -2, "#8d99a6")}
          <path d="M12 16l-2 4h3l-1 3" stroke="#FFC83D" strokeWidth="1.8" fill="none" />
        </>
      )}
    </svg>
  );
}
