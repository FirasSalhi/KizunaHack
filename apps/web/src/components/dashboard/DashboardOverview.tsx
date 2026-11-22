"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { fill, useI18n } from "@/i18n/I18nProvider";
import { IRRIGATION_CROP, IRRIGATION_METHOD, PLAN_EVENT, loadPlan, soilClass, type FarmPlan } from "@/lib/farmPlan";
import { apiClient } from "@/services/apiClient";
import { sensorService } from "@/services/sensorService";
import { getAssistant, setAssistantContext } from "@/components/assistant/farmAssistant";
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


/** Keep a label (440 px wide in photo pixels) inside the visible part of the cropped photo, left of the side panel. */
function clampLabel(x: number, box: { w: number; h: number } | null) {
  if (!box) return x;
  const scale = Math.max(box.w / 2816, box.h / 1584);
  const x0 = (2816 * scale - box.w) / 2 / scale;
  const panel = box.w >= 1280 ? 380 / scale : 0; // quick actions column (xl)
  const lo = x0 + 240, hi = x0 + box.w / scale - panel - 240;
  return Math.min(Math.max(x, lo), Math.max(lo, hi));
}

const PRIO_STYLE: Record<string, { pill: string; line: string; arrow: string }> = {
  HIGH: { pill: "#e53935", line: "#ff5a4e", arrow: "▲" },
  MEDIUM: { pill: "#f59e0b", line: "#ffb648", arrow: "●" },
  LOW: { pill: "#2e9d3a", line: "#53d14b", arrow: "▼" },
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
  const sunToday = weather?.days[0]?.radiation_kwh_m2 ?? null;
  const sunYesterday = weather?.yesterday?.radiation_kwh_m2 ?? null;
  const sunTrend = sunToday != null && sunYesterday ? ((sunToday - sunYesterday) / sunYesterday) * 100 : null;

  const nf = (d = 0) => new Intl.NumberFormat(locale, { maximumFractionDigits: d, minimumFractionDigits: d });
  const today = new Intl.DateTimeFormat(locale, { weekday: "short", day: "numeric", month: "short", year: "numeric" }).format(new Date());
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

  const alerts = urgent.length;

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
  const warnings = missing.size + (weatherFailed ? 1 : 0) + (engineState === "down" ? 1 : 0);

  return (
    <div className="relative">
      {/* ======== photo hero: the whole top of the page ======== */}
      <div ref={heroRef} className="relative overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/images/farmlink-field-aerial.jpg" alt="" className="absolute inset-0 w-full h-full object-cover object-top" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#1d4b78]/35 via-transparent to-[#2a1e10]/20" />

        {/* plot outlines and labels, drawn in the photo's own pixels (desktop) */}
        <svg viewBox="0 0 2816 1584" preserveAspectRatio="xMidYMin slice" className="absolute inset-0 w-full h-full hidden md:block" aria-label={t.mapLabel}>
          {plots.map((p, i) => {
            const f = FIELDS[i];
            const lv = levelOf(p.zoneId);
            const s = PRIO_STYLE[lv ?? "none"];
            const [fx, ly] = f.label;
            const lx = clampLabel(fx, box);
            return (
              <g key={p.zoneId}>
                <polygon points={f.pts} fill={s.line} fillOpacity={0.12} stroke={s.line} strokeWidth={7} strokeLinejoin="round" />
                <line x1={lx} y1={ly} x2={lx} y2={ly + 110} stroke="#fff" strokeWidth={4} />
                <circle cx={lx} cy={ly + 115} r={10} fill="#fff" />
                <foreignObject x={lx - 220} y={ly - 128} width={440} height={128}>
                  <div className="h-full flex items-end justify-center">
                    <div className="flex items-center gap-3 rounded-[22px] border-[3px] border-white/70 bg-[#2a2216]/85 px-5 py-3 shadow-2xl">
                      <span className="w-12 h-12 rounded-full grid place-items-center text-[30px] text-white" style={{ background: s.pill }}>
                        <CropIcon id={p.cropId} />
                      </span>
                      <span className="flex flex-col items-start">
                        <span className="text-[32px] font-bold text-white whitespace-nowrap leading-tight">{p.zoneId} · {p.name}</span>
                        <span className="mt-1 rounded-full px-3.5 py-0.5 text-[22px] font-semibold text-white whitespace-nowrap" style={{ background: s.pill }}>
                          {s.arrow ? `${s.arrow} ` : ""}{prioLabel(lv)}
                        </span>
                      </span>
                    </div>
                  </div>
                </foreignObject>
              </g>
            );
          })}
        </svg>

        <div className="relative px-4 sm:px-6 lg:px-8 pt-6 pb-8">
          {/* Header: greeting, live weather, date */}
          <header className="flex flex-col xl:flex-row xl:items-start gap-4 justify-between">
            <div className="min-w-0 [text-shadow:0_2px_12px_rgba(0,0,0,.55)]">
              <h1 className="text-3xl sm:text-[44px] font-extrabold text-white tracking-tight leading-tight">{fill(t.hello, { name })}</h1>
              <p className="text-base sm:text-xl text-white/95 mt-1">{fill(t.subtitle, { place })}</p>
              {!farmPlace && placeStatus !== "locating" && (
                <button
                  type="button"
                  onClick={locate}
                  className="mt-2 inline-flex items-center gap-2 rounded-full bg-[#2e9d3a] px-4 py-1.5 text-sm font-semibold text-white [text-shadow:none] shadow"
                >
                  {t.locateMe}
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-3">
              <WeatherPill weather={weather} failed={weatherFailed} t={t} nf={nf} />
              <div className="flex items-center gap-3 rounded-2xl bg-[#25415a]/70 backdrop-blur-md border border-white/20 px-5 py-3 text-base text-white shadow-lg">
                <span className="text-2xl"><IconCalendar /></span> <span className="capitalize font-medium">{today}</span>
              </div>
            </div>
          </header>

          {/* Middle: photo space (plots) + quick actions & assistant */}
          <div className="mt-6 grid grid-cols-1 xl:grid-cols-[1fr_330px] gap-5">
            <div className="min-h-[260px] md:min-h-[430px] relative">
              {!plots.length && (
                <div className="absolute left-0 bottom-4 max-w-md rounded-2xl bg-white/90 text-[#1d2b1a] p-4 shadow-xl">
                  <p className="font-semibold">{t.noPlanMap}</p>
                  <Link href="/dashboard/planning" className="inline-flex mt-3 rounded-lg bg-[#2e7d32] text-white font-semibold text-sm px-3 py-2">{t.planCta}</Link>
                </div>
              )}
            </div>
            <aside className="space-y-4">
              <div className="rounded-3xl bg-[#173a1f]/90 backdrop-blur-md border border-white/15 p-4 space-y-3 shadow-2xl">
                <h2 className="text-xl font-bold text-white">{t.quickTitle}</h2>
                <QuickLink href="/dashboard/irrigation-3d" icon={<IconDropFill />} label={t.qIrrigate} />
                <QuickLink href="/dashboard/planning" icon={<IconSproutFill />} label={t.qPlan} />
                <QuickLink href="/dashboard/scanner" icon={<IconCameraFill />} label={t.qScan} />
                <QuickLink href="/dashboard/market" icon={<IconShopFill />} label={t.qMarket} />
              </div>
              <Assistant t={t} />
            </aside>
          </div>

          {/* phones: plot list under the photo area */}
          {plots.length > 0 && (
            <ul className="md:hidden mt-4 rounded-2xl bg-white/92 divide-y divide-black/5 shadow-lg">
              {plots.map((p) => {
                const lv = levelOf(p.zoneId);
                return (
                  <li key={p.zoneId} className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#1d2b1a]">
                    <span className="text-lg text-[#2e7d32]"><CropIcon id={p.cropId} /></span>
                    <span className="font-semibold">{p.zoneId} · {p.name}</span>
                    <span className="ms-auto rounded-full px-2 py-0.5 text-xs font-semibold text-white" style={{ background: PRIO_STYLE[lv ?? "none"].pill }}>{prioLabel(lv)}</span>
                  </li>
                );
              })}
            </ul>
          )}

          {/* KPI cards */}
          <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-[1.3fr_1.2fr_0.8fr_0.9fr] gap-4 xl:me-[350px]">
            <Card className="flex items-center gap-3 !p-4">
              <Bubble className="bg-[#e3f2fd] text-[#1e88e5]"><IconDropFill /></Bubble>
              <div className="min-w-0 flex-1">
                <div className="text-[15px] text-[#33402f]">{t.kWater}</div>
                <div className="text-[26px] font-bold text-[#17220f] leading-tight tabular-nums whitespace-nowrap">
                  {!plan ? "—" : engine ? `${nf(0).format(waterToday)} m³` : engineState === "down" ? "—" : "…"}
                </div>
                <div className="text-xs text-[#5d6b58]">{!plan ? t.kNeedPlan : engine ? fill(t.kWaterSub, { n: urgent.length }) : engineState === "down" ? t.kEngineDown : t.computing}</div>
              </div>
              <Ring value={soil} label={t.kSoilRing} />
            </Card>
            <Card className="flex items-center gap-3 !p-4">
              <Bubble className="bg-[#fff6dd] text-[#f5a300]"><IconSunFill /></Bubble>
              <div className="min-w-0">
                <div className="text-[15px] text-[#33402f]">{t.kSun}</div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[26px] font-bold text-[#17220f] leading-tight tabular-nums whitespace-nowrap">{sunToday == null ? "—" : `${nf(1).format(sunToday)} kWh/m²`}</span>
                  {sunTrend != null && (
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${sunTrend >= 0 ? "bg-[#e6f6df] text-[#2e7d32]" : "bg-[#fdeaea] text-[#c62828]"}`}>
                      {sunTrend >= 0 ? "▲" : "▼"} {sunTrend >= 0 ? "+" : ""}{nf(0).format(sunTrend)} %
                    </span>
                  )}
                </div>
                <div className="text-xs text-[#5d6b58]">{sunToday == null ? (weatherFailed ? t.weatherDown : t.computing) : t.kSunSub}</div>
              </div>
            </Card>
            <Card className="flex items-center gap-3 !p-4">
              <Bubble className="bg-[#e8f5e0] text-[#2e7d32]"><IconPlotsFill /></Bubble>
              <div>
                <div className="text-[15px] text-[#33402f]">{t.kPlots}</div>
                <div className="text-[26px] font-bold text-[#17220f] leading-tight tabular-nums whitespace-nowrap">{plan ? plan.crops.length : 0}</div>
                <div className="text-xs text-[#5d6b58]">{plan ? fill(t.kPlotsSub, { ha: nf(1).format(plan.area_ha) }) : t.kNeedPlan}</div>
              </div>
            </Card>
            <Card className={`flex items-center gap-4 ${alerts ? "bg-gradient-to-r from-white to-[#fdeceb]" : ""}`}>
              <Bubble className="bg-[#fdeceb] text-[#e53935]"><IconBellFill /></Bubble>
              <div>
                <div className="text-[15px] text-[#33402f]">{t.kAlerts}</div>
                <div className={`text-[24px] font-bold leading-tight ${alerts ? "text-[#e53935]" : warnings ? "text-[#d97706]" : "text-[#2e7d32]"}`}>
                  {alerts ? fill(t.kAlertsUrgent, { n: alerts }) : warnings ? fill(t.kAlertsWarn, { n: warnings }) : t.kAlertsNone}
                </div>
                <div className="text-xs text-[#5d6b58]">{alerts ? t.kAlertsUrgentSub : warnings ? t.kAlertsWarnSub : t.kAlertsNoneSub}</div>
              </div>
            </Card>
          </div>

          {/* Field-unit live readings (IoT feed and API unchanged), shown with the other cards */}
          <div className="mt-6">
            <FieldSensors cards />
          </div>

          {/* Recommendation + forecast */}
          <div className="mt-5 grid grid-cols-1 xl:grid-cols-[1.4fr_1fr] gap-5">
            <Card>
              <h2 className="text-xl font-bold text-[#17220f] flex items-center gap-2"><span className="text-[#2e7d32]"><IconSparkle /></span> {t.recoTitle}</h2>
              <Link
                href={reco.href}
                className={`mt-3 flex items-center gap-4 rounded-2xl p-4 transition-colors ${reco.tone === "warn" ? "bg-[#fff4e0]" : "bg-[#eaf6e3] hover:bg-[#dff0d5]"}`}
              >
                <Bubble className="bg-white text-[#2e9d3a]"><IconDropFill /></Bubble>
                <span className="min-w-0 flex-1">
                  <span className="block text-lg sm:text-[22px] font-bold text-[#17220f]">{reco.title}</span>
                  {reco.text && <span className="block text-[15px] text-[#3c4a37] mt-0.5">{reco.text}</span>}
                </span>
                <span className="grid place-items-center w-11 h-11 rounded-xl bg-[#2e7d32] text-white shrink-0 text-2xl font-bold" aria-hidden="true">›</span>
              </Link>
              {plan && <p className="text-xs text-[#6b7865] mt-2">{t.recoAssume}</p>}
            </Card>

            <Card>
              <h2 className="text-xl font-bold text-[#17220f]">{t.forecastTitle}</h2>
              {weather && weather.days.length > 1 ? (
                <ol className="mt-3 grid grid-cols-5 divide-x divide-black/10">
                  {weather.days.slice(1, 6).map((day) => (
                    <li key={day.date} className="flex flex-col items-center gap-2 px-1 text-center">
                      <span className="text-[15px] text-[#33402f] capitalize">{new Intl.DateTimeFormat(locale, { weekday: "short" }).format(new Date(`${day.date}T12:00:00`))}</span>
                      <WeatherIcon cond={day.condition} size={34} />
                      <span className="text-[15px] text-[#17220f] tabular-nums font-semibold">
                        {day.tmax_c == null ? "—" : Math.round(day.tmax_c)}°<span className="text-[#6b7865] font-normal">/{day.tmin_c == null ? "—" : Math.round(day.tmin_c)}°</span>
                      </span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="mt-3 text-sm text-[#5d6b58]">{weatherFailed ? t.weatherDown : t.computing}</p>
              )}
            </Card>
          </div>
        </div>
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

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-3xl bg-white/[0.96] p-5 shadow-[0_10px_30px_rgba(0,0,0,0.18)] text-[#17220f] min-w-0 ${className}`}>{children}</div>;
}

function Bubble({ children, className }: { children: React.ReactNode; className: string }) {
  return <span className={`grid place-items-center w-12 h-12 rounded-full shrink-0 text-[24px] ${className}`}>{children}</span>;
}

/** Soil-water gauge from the field unit (null = no fresh reading). */
function Ring({ value, label }: { value: number | null; label: string }) {
  const r = 26, c = 2 * Math.PI * r, v = value == null ? 0 : Math.max(0, Math.min(100, value));
  const color = value == null ? "#c7cdc4" : v <= 20 ? "#e53935" : v <= 35 ? "#f59e0b" : "#2e7d32";
  return (
    <div className="relative w-[68px] h-[68px] shrink-0" title={label}>
      <svg viewBox="0 0 64 64" className="w-full h-full -rotate-90" aria-hidden="true">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#e5ebe2" strokeWidth="7" />
        <circle cx="32" cy="32" r={r} fill="none" stroke={color} strokeWidth="7" strokeDasharray={`${(c * v) / 100} ${c}`} strokeLinecap="round" />
      </svg>
      <span className="absolute inset-0 grid place-items-center text-center leading-none">
        <span className="text-[15px] font-bold text-[#17220f]">{value == null ? "—" : `${Math.round(v)}%`}</span>
      </span>
      <span className="absolute -bottom-4 inset-x-0 text-center text-[10px] text-[#5d6b58]">{label}</span>
    </div>
  );
}

function WeatherPill({ weather, failed, t, nf }: { weather: Weather | null; failed: boolean; t: T; nf: (d?: number) => Intl.NumberFormat }) {
  const box = "flex flex-wrap items-center gap-3 sm:gap-5 rounded-[26px] bg-[#25415a]/70 backdrop-blur-md border border-white/20 px-4 sm:px-6 py-3 text-white shadow-lg max-w-full";
  if (!weather) return <div className={box}>{failed ? t.weatherDown : t.computing}</div>;
  const c = weather.current;
  const wx = t.wx as Record<string, string>;
  return (
    <div className={box}>
      <WeatherIcon cond={c.condition} size={46} />
      <div>
        <div className="text-[26px] sm:text-[32px] font-bold tabular-nums leading-none">{c.temperature_c == null ? "—" : nf(0).format(c.temperature_c)}°C</div>
        <div className="text-sm text-white/90 mt-1">{wx[c.condition] ?? ""}</div>
      </div>
      <span className="hidden sm:block w-px self-stretch bg-white/25" />
      <span className="text-base sm:text-lg inline-flex items-center gap-2 whitespace-nowrap" title={t.wind}><IconWind /> {c.wind_kmh == null ? "—" : nf(0).format(c.wind_kmh)} km/h</span>
      <span className="hidden sm:block w-px self-stretch bg-white/25" />
      <span className="text-base sm:text-lg inline-flex items-center gap-2 whitespace-nowrap" title={t.humidity}><IconDropLine /> {c.humidity_pct == null ? "—" : nf(0).format(c.humidity_pct)}%</span>
    </div>
  );
}

function QuickLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="flex items-center gap-4 rounded-2xl bg-gradient-to-r from-[#f3fbe9] to-[#e2f3d2] px-4 py-3.5 font-bold text-[#17330f] text-[17px] shadow hover:from-white hover:to-[#eaf7dc] transition-colors">
      <span className="text-[28px] text-[#2e9d3a]">{icon}</span>
      {label}
    </Link>
  );
}

/** Typed questions go to the same voice assistant as the bubble (answer shown here and read aloud). */
function Assistant({ t }: { t: T }) {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const ask = async () => {
    const text = q.trim();
    if (!text || busy) return;
    setBusy(true);
    setAnswer(null);
    try {
      setAnswer(await getAssistant().askTyped(text));
      setQ("");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div id="assistant" className="rounded-3xl bg-[#173a1f]/90 backdrop-blur-md border border-white/15 p-4 shadow-2xl scroll-mt-6">
      <div className="flex items-center gap-3">
        <button type="button" onClick={() => getAssistant().openListening()} className="text-[34px] text-[#9be070]" aria-label={t.assistantTitle}>
          <IconBot />
        </button>
        <div>
          <h2 className="text-xl font-bold text-white">{t.assistantTitle}</h2>
          <p className="text-sm text-white/85">{t.assistantSub}</p>
        </div>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask();
        }}
        className="mt-3 rounded-2xl bg-white p-3"
      >
        <textarea
          value={q}
          onChange={(e) => setQ(e.target.value)}
          rows={2}
          placeholder={t.assistantPh}
          aria-label={t.assistantSub}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask();
            }
          }}
          className="w-full resize-none bg-transparent text-sm text-[#17220f] placeholder:text-[#7b8676] outline-none"
        />
        <div className="flex justify-end">
          <button type="submit" disabled={busy} className="grid place-items-center w-11 h-11 rounded-xl bg-[#2e9d3a] text-white text-xl disabled:opacity-60" aria-label={t.send}>
            <IconSend />
          </button>
        </div>
      </form>
      {answer && <div className="mt-3 rounded-2xl bg-white/95 p-3 text-sm text-[#17220f]">{answer}</div>}
      <p className="text-[11px] text-white/60 mt-2">{t.assistantNote}</p>
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
const IconDropFill = () => solid("M12 2.5c3.9 4.6 6.6 8.3 6.6 11.4a6.6 6.6 0 0 1-13.2 0C5.4 10.8 8.1 7.1 12 2.5Z");
const IconDropLine = () => line("M12 3c3.5 4.2 6 7.6 6 10.6A6 6 0 0 1 6 13.6C6 10.6 8.5 7.2 12 3Z");
const IconSproutFill = () => solid("M11 21v-7.2C7.2 13.4 4.5 10.5 4.5 6.5 8.6 6.6 11 9.3 11.2 12c.6-4.2 3.5-7 8.3-7 0 4.6-3 7.8-7 8.1V21h-1.5Z");
const IconCameraFill = () => solid("M8.5 4 7 6H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-3l-1.5-2h-7ZM12 9a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z");
const IconShopFill = () => solid("M4 3h16l2 6a3 3 0 0 1-5 2.2A3 3 0 0 1 12 11a3 3 0 0 1-5 .2A3 3 0 0 1 2 9l2-6Zm0 9.5c1 .4 2.1.4 3 0V20h4v-4h2v4h4v-7.5c.9.4 2 .4 3 0V21H4v-8.5Z");
const IconSunFill = () => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" aria-hidden="true">
    <circle cx="12" cy="12" r="5" fill="currentColor" />
    <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">{[0, 45, 90, 135, 180, 225, 270, 315].map((a) => <line key={a} x1="12" y1="1.8" x2="12" y2="4" transform={`rotate(${a} 12 12)`} />)}</g>
  </svg>
);
const IconPlotsFill = () => line("M3 20 7 6h14l-4 14H3Zm2.5-7h14M12 6l-3 14");
const IconBellFill = () => line("M6 16V11a6 6 0 1 1 12 0v5l2 2H4l2-2Zm4 4a2 2 0 0 0 4 0");
const IconSparkle = () => line("M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8L12 3Zm7 11 .8 2.2 2.2.8-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14Z");
const IconBot = () => line("M12 3v3m-6 3h12a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2Zm3 5h.01M15 14h.01M9.5 17h5M2 13v2M22 13v2");
const IconSend = () => solid("M3 11.5 20.5 3.6c.6-.3 1.2.3.9.9L13.5 22c-.3.6-1.1.5-1.3-.1l-1.9-6.2-6.2-1.9c-.6-.2-.7-1-.1-1.3Z");
const IconWind = () => line("M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h7");
const IconCalendar = () => line("M4 6h16v14H4V6Zm0 4h16M8 3v4m8-4v4M8 14h2m4 0h2");

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
