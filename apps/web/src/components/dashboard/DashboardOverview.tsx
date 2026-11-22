"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { fill, useI18n } from "@/i18n/I18nProvider";
import { IRRIGATION_CROP, IRRIGATION_METHOD, PLAN_EVENT, loadPlan, soilClass, type FarmPlan } from "@/lib/farmPlan";
import { apiClient } from "@/services/apiClient";
import { sensorService } from "@/services/sensorService";
import { setAssistantContext } from "@/components/assistant/farmAssistant";
import { placeLabel, usePlace } from "@/lib/place";
import { FieldSensors } from "./FieldSensors";

/*
 * Dashboard home (design "Bonjour Sami"). Every number comes from a live source; nothing is typed in:
 *  - weather, sunshine and the 5-day forecast: GET /api/v1/weather (Open-Meteo through the FARMLINK API);
 *  - plots: the crop plan validated in Crop Planning (lib/farmPlan.ts);
 *  - priorities, water to apply, alerts, recommendation: POST /api/v1/irrigation/farm (FAO-56 engine);
 *  - soil water gauge: the field unit (GET /api/v1/sensors/latest), and the full IoT block below (unchanged).
 */

// Soil water at field capacity / wilting point per texture class: same table as Irrigation 3D (ferme_3d.html).
const SOIL_FC_WP: Record<string, { fc: number; wp: number }> = {
  loamy_sand: { fc: 0.15, wp: 0.06 }, sandy_loam: { fc: 0.22, wp: 0.1 }, loam: { fc: 0.25, wp: 0.11 },
  clay_loam: { fc: 0.3, wp: 0.15 }, silt: { fc: 0.32, wp: 0.15 }, silty_clay: { fc: 0.35, wp: 0.23 },
};
// Like Irrigation 3D, the last full irrigation is assumed 3 days ago (the page says so).
const LAST_IRRIGATION_DAYS = 3;
// Fields of the aerial photo (pixels of farmlink-field-aerial.jpg, 2816 x 1584): outline + label anchor.
const FIELDS: { pts: string; label: [number, number] }[] = [
  { pts: "655,500 1430,505 1125,770 425,712", label: [880, 470] },
  { pts: "990,815 1630,852 1585,1584 680,1584", label: [1120, 790] },
  { pts: "1455,503 1745,514 1680,808 1135,770", label: [1520, 478] },
  { pts: "0,760 850,755 720,1250 0,1250", label: [330, 730] },
  { pts: "1860,490 2816,568 2816,808 1838,765", label: [2140, 500] },
  { pts: "1860,985 2816,1050 2816,1584 1790,1584", label: [2160, 960] },
];

type Day = { date: string; condition: string; tmax_c: number | null; tmin_c: number | null; radiation_kwh_m2: number | null };
type Weather = {
  current: { temperature_c: number | null; humidity_pct: number | null; wind_kmh: number | null; condition: string };
  yesterday: Day | null;
  days: Day[];
};
type EngineZone = { zone_id: string; timing?: string; dr_mm?: number; volumes?: { m3: number } | null };
type EngineResult = {
  zones: EngineZone[];
  ranking: { rank: number; zone_id: string; level: "HIGH" | "MEDIUM" | "LOW" }[];
  needs_data: { zone_id: string }[];
};
type Plot = { zoneId: string; name: string; cropId: string; area: number };
type Reco = { tone: "go" | "ok" | "info" | "warn"; title: string; text: string; href: string };
type Level = "HIGH" | "MEDIUM" | "LOW" | "missing" | undefined;

function stageOf(sowing: number | null, perennial: boolean, month: number) {
  if (perennial || !sowing) return "mid_season";
  const m = (month - sowing + 12) % 12;
  return m <= 1 ? "initial" : m <= 2 ? "development" : m <= 4 ? "mid_season" : m <= 6 ? "late_season" : "initial";
}

function plotsOf(plan: FarmPlan | null): Plot[] {
  return (plan?.crops ?? [])
    .filter((c) => IRRIGATION_CROP[c.id])
    .slice(0, 6)
    .map((c, i) => ({ zoneId: `Z${i + 1}`, name: c.name, cropId: c.id, area: Math.max(0.1, Math.round(c.area_ha * 100) / 100) }));
}


/**
 * Where the photo's pixels land on screen: the photo covers the hero (object-cover, top-aligned), so it is scaled
 * by the larger ratio and centred horizontally. Labels are placed with this, at a fixed readable size.
 */
function photoGeometry(box: { w: number; h: number } | null) {
  if (!box) return null;
  const s = Math.max(box.w / 2816, box.h / 1584);
  return { s, ox: (box.w - 2816 * s) / 2 };
}
// Plot labels stay inside the photo.
const LABEL_HALF = 120;
const EDGE = 16;

const PRIO_STYLE: Record<string, { pill: string; line: string; arrow: string; ink?: string }> = {
  HIGH: { pill: "#e53935", line: "#ff5a4e", arrow: "▲" },
  MEDIUM: { pill: "#f59e0b", line: "#ffb648", arrow: "●" },
  LOW: { pill: "#c6f04a", line: "#c6f04a", arrow: "▼", ink: "#0d0f0c" },
  missing: { pill: "#6b7280", line: "#cfd6dd", arrow: "" },
  none: { pill: "#6b7280", line: "#ffffff", arrow: "" },
};

export function DashboardOverview() {
  const { user } = useAuth();
  const { m, locale } = useI18n();
  const t = m.home;
  const [plan, setPlan] = useState<FarmPlan | null>(null);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [weatherFailed, setWeatherFailed] = useState(false);
  const [engine, setEngine] = useState<EngineResult | null>(null);
  const [engineState, setEngineState] = useState<"idle" | "loading" | "down">("idle");
  const [soil, setSoil] = useState<number | null>(null);
  const [box, setBox] = useState<{ w: number; h: number } | null>(null);
  const heroRef = React.useRef<HTMLDivElement>(null);
  const assistantContextRef = React.useRef<Record<string, unknown>>({});

  // Size of the photo area, to keep plot labels inside the visible part of the cropped photo.
  useEffect(() => {
    const el = heroRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setBox({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

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

  const { place: farmPlace, status: placeStatus, locate } = usePlace();
  const plots = useMemo(() => plotsOf(plan), [plan]);

  // Weather through the FARMLINK API (Open-Meteo), refreshed every 15 minutes.
  const pointLat = farmPlace?.lat ?? null;
  const pointLon = farmPlace?.lon ?? null;
  useEffect(() => {
    if (pointLat == null || pointLon == null) return;
    let alive = true;
    const load = async () => {
      try {
        const data = await apiClient<Weather>(`/weather?lat=${pointLat}&lon=${pointLon}`);
        if (alive) {
          setWeather(data);
          setWeatherFailed(false);
        }
      } catch {
        if (alive) setWeatherFailed(true);
      }
    };
    void load();
    const timer = setInterval(load, 15 * 60 * 1000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [pointLat, pointLon]);

  // Soil moisture from the field unit for the water gauge (read only; the IoT feed is unchanged).
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const snap = await sensorService.latest();
        const dev = snap.devices.find((d) => d.latest) ?? snap.devices[0];
        const fresh = dev?.latest && (dev.age_s ?? Infinity) <= 60;
        if (alive) setSoil(fresh ? dev.latest!.soil_moisture : null);
      } catch {
        if (alive) setSoil(null);
      }
    };
    void load();
    const timer = setInterval(load, 10000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  // Irrigation engine on the planned plots (same inputs as Irrigation 3D).
  const runEngine = useCallback(async () => {
    if (!plan || !plots.length) {
      setEngine(null);
      setEngineState("idle");
      return;
    }
    setEngineState("loading");
    const soilFcWp = SOIL_FC_WP[soilClass(plan.soil)];
    const month = new Date().getMonth() + 1;
    const refill = new Date(Date.now() - LAST_IRRIGATION_DAYS * 86400000).toISOString().slice(0, 10);
    const crops = new Map(plan.crops.map((c) => [c.id, c]));
    try {
      const res = await apiClient<EngineResult>("/irrigation/farm", {
        method: "POST",
        body: JSON.stringify({
          farm_id: "home",
          location: { lat: plan.location.lat, lon: plan.location.lon, elevation_m: 0 },
          zones: plots.map((p) => {
            const c = crops.get(p.cropId);
            return {
              zone_id: p.zoneId,
              name: p.name,
              crop: IRRIGATION_CROP[p.cropId],
              area_ha: p.area,
              stage_override: stageOf(c?.sowing_month ?? null, c?.perennial ?? false, month),
              ...(soilFcWp ? { soil: soilFcWp } : {}),
              irrigation: { method: IRRIGATION_METHOD[plan.irrigation_method ?? ""] ?? "drip" },
              last_refill_date: refill,
            };
          }),
        }),
      });
      setEngine(res);
      setEngineState("idle");
    } catch {
      setEngine(null);
      setEngineState("down");
    }
  }, [plan, plots]);

  useEffect(() => {
    void runEngine();
    const timer = setInterval(() => void runEngine(), 30 * 60 * 1000);
    return () => clearInterval(timer);
  }, [runEngine]);

  // ---- derived values (all from the live sources above) ----
  const zone = (id: string) => engine?.zones.find((z) => z.zone_id === id);
  const missing = new Set(engine?.needs_data.map((n) => n.zone_id) ?? []);
  const levelOf = (id: string): Level => (missing.has(id) ? "missing" : engine?.ranking.find((r) => r.zone_id === id)?.level);
  const urgent = engine?.zones.filter((z) => z.timing === "irrigate_now") ?? [];
  const waterToday = urgent.reduce((s, z) => s + (z.volumes?.m3 ?? 0), 0);
  const top = engine?.ranking[0];
  const topZone = top ? zone(top.zone_id) : undefined;
  const topPlot = top ? plots.find((p) => p.zoneId === top.zone_id) : undefined;

  const nf = (d = 0) => new Intl.NumberFormat(locale, { maximumFractionDigits: d, minimumFractionDigits: d });
  const name = user?.name?.split(" ")[0] || t.farmer;
  const place = farmPlace
    ? placeLabel(farmPlace, (town) => fill(t.placeNear, { town }))
    : placeStatus === "locating" ? t.placeLocating : t.placeUnknown;
  const prioLabel = (lv: Level) =>
    lv === "HIGH" ? t.prioHigh : lv === "MEDIUM" ? t.prioMedium : lv === "LOW" ? t.prioLow : lv === "missing" ? t.prioMissing : engineState === "down" ? t.prioUnknown : t.computing;

  let reco: Reco;
  if (!plan || !plots.length) reco = { tone: "info", title: t.recoNoPlan, text: t.recoNoPlanText, href: "/dashboard/planning" };
  else if (engineState === "down") reco = { tone: "warn", title: t.recoApiDown, text: t.recoApiDownText, href: "/dashboard/irrigation-3d" };
  else if (!engine) reco = { tone: "info", title: t.computing, text: "", href: "/dashboard/irrigation-3d" };
  else if (topZone?.timing === "irrigate_now" && topPlot)
    reco = {
      tone: "go",
      title: fill(t.recoIrrigate, { zone: topPlot.zoneId, crop: topPlot.name }),
      text: fill(t.recoIrrigateText, { mm: nf(0).format(topZone.dr_mm ?? 0), m3: nf(0).format(topZone.volumes?.m3 ?? 0) }),
      href: "/dashboard/irrigation-3d",
    };
  else if (topZone?.timing?.startsWith("irrigate_within_") && topPlot)
    reco = {
      tone: "ok",
      title: fill(t.recoSoon, { zone: topPlot.zoneId, crop: topPlot.name, days: topZone.timing.replace(/\D/g, "") }),
      text: fill(t.recoSoonText, { mm: nf(0).format(topZone.dr_mm ?? 0) }),
      href: "/dashboard/irrigation-3d",
    };
  else reco = { tone: "ok", title: t.recoNone, text: t.recoNoneText, href: "/dashboard/irrigation-3d" };


  // What the voice assistant knows about the farm: exactly what this page shows.
  const assistantContext = {
    place,
    weather: weather
      ? { ...weather.current, sky: (t.wx as Record<string, string>)[weather.current.condition] ?? weather.current.condition, next_days: weather.days.slice(1, 6) }
      : null,
    plots: plots.map((p) => ({ id: p.zoneId, crop: p.name, area_ha: p.area, priority: levelOf(p.zoneId) ?? null })),
    recommendation: { title: reco.title, text: reco.text },
    water_to_apply_today_m3: engine ? waterToday : null,
    sensors: { soil_moisture: soil },
  };
  useEffect(() => {
    setAssistantContext(() => assistantContextRef.current);
  }, []);
  assistantContextRef.current = assistantContext;
  // Plot labels in screen pixels (wide screens, where the whole photo is shown).
  const geo = photoGeometry(box);
  const labelX = (fx: number) => {
    if (!geo || !box) return fx;
    const x = geo.ox + fx * geo.s;
    const lo = LABEL_HALF + EDGE, hi = box.w - LABEL_HALF - EDGE;
    return Math.min(Math.max(x, lo), Math.max(lo, hi));
  };

  return (
    <div className="relative">
      {/* ======== photo hero: greeting, weather and the plots on the aerial photo ======== */}
      {/* Wide screens show the whole photo (its own 16:9 shape); narrower ones show a band of it. */}
      <div ref={heroRef} className="relative w-full overflow-hidden xl:aspect-[2816/1584] xl:max-h-[78svh] flex flex-col">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/images/farmlink-field-aerial.jpg" alt="" className="absolute inset-0 w-full h-full object-cover object-top" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/35 via-transparent to-[#020302]" />

        {/* plot outlines, drawn in the photo's own pixels (wide screens) */}
        {geo && (
          <svg viewBox="0 0 2816 1584" preserveAspectRatio="xMidYMin slice" className="absolute inset-0 w-full h-full hidden xl:block" aria-label={t.mapLabel}>
            {plots.map((p, i) => {
              const f = FIELDS[i];
              const s = PRIO_STYLE[levelOf(p.zoneId) ?? "none"];
              const lx = (labelX(f.label[0]) - geo.ox) / geo.s, ly = f.label[1];
              return (
                <g key={p.zoneId}>
                  <polygon points={f.pts} fill={s.line} fillOpacity={0.12} stroke={s.line} strokeWidth={3} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
                  <line x1={lx} y1={ly} x2={lx} y2={ly + 110} stroke="#fff" strokeWidth={2} vectorEffect="non-scaling-stroke" />
                  <circle cx={lx} cy={ly + 115} r={5 / geo.s} fill="#fff" />
                </g>
              );
            })}
          </svg>
        )}
        {/* plot labels, at a fixed size whatever the photo's scale */}
        {geo &&
          plots.map((p, i) => {
            const lv = levelOf(p.zoneId);
            const s = PRIO_STYLE[lv ?? "none"];
            const [fx, fy] = FIELDS[i].label;
            return (
              <div
                key={p.zoneId}
                className="absolute z-[1] hidden xl:flex items-center gap-2 rounded-2xl border-2 border-white/70 bg-[#0d0f0c]/85 px-2.5 py-1.5 shadow-xl -translate-x-1/2 -translate-y-full pointer-events-none"
                style={{ left: labelX(fx), top: fy * geo.s }}
              >
                <span className="w-8 h-8 rounded-full grid place-items-center text-lg shrink-0" style={{ background: s.pill, color: s.ink ?? "#fff" }}>
                  <CropIcon id={p.cropId} />
                </span>
                <span className="flex flex-col items-start">
                  <span className="text-sm font-bold text-white whitespace-nowrap leading-tight">{p.zoneId} · {p.name}</span>
                  <span className="mt-0.5 rounded-full px-2 py-px text-[11px] font-semibold whitespace-nowrap" style={{ background: s.pill, color: s.ink ?? "#fff" }}>
                    {s.arrow ? `${s.arrow} ` : ""}{prioLabel(lv)}
                  </span>
                </span>
              </div>
            );
          })}

        <div className="relative flex-1 flex flex-col px-4 sm:px-6 lg:px-8 pt-5 pb-5">
          {/* Header: greeting and live weather */}
          <header className="flex flex-col xl:flex-row xl:items-start gap-3 justify-between">
            <div className="min-w-0 [text-shadow:0_2px_12px_rgba(0,0,0,.55)]">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-tight">{fill(t.hello, { name })}</h1>
              <p className="text-sm sm:text-base text-white/95 mt-1">{fill(t.subtitle, { place })}</p>
              {!farmPlace && placeStatus !== "locating" && (
                <button
                  type="button"
                  onClick={locate}
                  className="mt-2 inline-flex items-center gap-2 rounded-full bg-[#c6f04a] px-4 py-1.5 text-sm font-semibold text-[#0d0f0c] [text-shadow:none] shadow"
                >
                  {t.locateMe}
                </button>
              )}
            </div>
            <WeatherPill weather={weather} failed={weatherFailed} t={t} nf={nf} />
          </header>

          {/* Plots on the photo (labels on wide screens, a list on narrower ones) */}
          <div className="mt-6 flex-1 min-h-[160px] md:min-h-[220px] flex flex-col justify-end">
            {!plots.length && (
              <div className="max-w-md rounded-2xl bg-[#0d0f0c]/90 border border-white/10 text-white p-4 shadow-xl">
                <p className="font-semibold">{t.noPlanMap}</p>
                <Link href="/dashboard/planning" className="inline-flex mt-3 rounded-lg bg-[#c6f04a] text-[#0d0f0c] font-semibold text-sm px-3 py-2">{t.planCta}</Link>
              </div>
            )}
            {plots.length > 0 && (
              <ul className="xl:hidden max-w-xl rounded-2xl bg-[#0d0f0c]/90 border border-white/10 divide-y divide-white/10 shadow-lg">
                {plots.map((p) => {
                  const lv = levelOf(p.zoneId);
                  return (
                    <li key={p.zoneId} className="flex items-center gap-3 px-4 py-2.5 text-sm text-white">
                      <span className="text-lg text-[#c6f04a]"><CropIcon id={p.cropId} /></span>
                      <span className="font-semibold">{p.zoneId} · {p.name}</span>
                      <span className="ms-auto rounded-full px-2 py-0.5 text-xs font-semibold" style={{ background: PRIO_STYLE[lv ?? "none"].pill, color: PRIO_STYLE[lv ?? "none"].ink ?? "#fff" }}>{prioLabel(lv)}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* ======== below the photo: the field unit's live readings (IoT feed and API unchanged) ======== */}
      <div className="bg-gradient-to-b from-[#020302] to-[#020302] px-4 sm:px-6 lg:px-8 pt-4 pb-6">
        <FieldSensors cards />
      </div>

      <p className="px-4 sm:px-6 lg:px-8 py-4 text-xs text-neutral-500">{t.sources}</p>
    </div>
  );
}

// ---------------------------------------------------------------- pieces
type T = ReturnType<typeof useI18n>["m"]["home"];

const TREES = new Set(["olive", "orange", "mandarin_jp", "almond", "pistachio", "apricot", "fig", "pomegranate", "date_palm", "grape"]);
const GRAINS = new Set(["wheat", "durum_wheat", "barley", "alfalfa", "chickpea", "faba_bean", "pea"]);

/** Simple crop pictogram: tree crops, grains, or vegetables. */
function CropIcon({ id }: { id: string }) {
  if (TREES.has(id)) return solid("M12 2a6 6 0 0 1 5.6 8.2A4.5 4.5 0 0 1 15.5 19H13v3h-2v-3H8.5a4.5 4.5 0 0 1-2.1-8.8A6 6 0 0 1 12 2Z");
  if (GRAINS.has(id)) return line("M12 22V8m0 4c-2-1-3-3-3-5 2 1 3 3 3 5Zm0 0c2-1 3-3 3-5-2 1-3 3-3 5Zm0 4c-2-1-3-3-3-5 2 1 3 3 3 5Zm0 0c2-1 3-3 3-5-2 1-3 3-3 5ZM12 8c-1-1.5-1-3.5 0-5 1 1.5 1 3.5 0 5Z");
  return solid("M11 21v-7.2C7.2 13.4 4.5 10.5 4.5 6.5 8.6 6.6 11 9.3 11.2 12c.6-4.2 3.5-7 8.3-7 0 4.6-3 7.8-7 8.1V21h-1.5Z");
}

function WeatherPill({ weather, failed, t, nf }: { weather: Weather | null; failed: boolean; t: T; nf: (d?: number) => Intl.NumberFormat }) {
  // No panel: plain text on the photo, with a shadow so it stays readable.
  const box = "flex flex-wrap items-center gap-x-4 gap-y-1 text-white max-w-full [text-shadow:0_1px_8px_rgba(0,0,0,.6)]";
  if (!weather) return <div className={`${box} text-sm`}>{failed ? t.weatherDown : t.computing}</div>;
  const c = weather.current;
  const wx = t.wx as Record<string, string>;
  return (
    <div className={box}>
      <span className="inline-flex items-center gap-2">
        <WeatherIcon cond={c.condition} size={28} />
        <span className="text-xl font-bold tabular-nums leading-none">{c.temperature_c == null ? "—" : nf(0).format(c.temperature_c)}°C</span>
        <span className="text-sm text-white/90">{wx[c.condition] ?? ""}</span>
      </span>
      <span className="text-sm inline-flex items-center gap-1.5 whitespace-nowrap" title={t.wind}><IconWind /> {c.wind_kmh == null ? "—" : nf(0).format(c.wind_kmh)} km/h</span>
      <span className="text-sm inline-flex items-center gap-1.5 whitespace-nowrap" title={t.humidity}><IconDropLine /> {c.humidity_pct == null ? "—" : nf(0).format(c.humidity_pct)}%</span>
    </div>
  );
}

// ---------------------------------------------------------------- icons
const line = (d: string) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
);
const solid = (d: string) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d={d} /></svg>
);
const IconDropLine = () => line("M12 3c3.5 4.2 6 7.6 6 10.6A6 6 0 0 1 6 13.6C6 10.6 8.5 7.2 12 3Z");
const IconWind = () => line("M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h7");

function WeatherIcon({ cond, size }: { cond: string; size: number }) {
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
