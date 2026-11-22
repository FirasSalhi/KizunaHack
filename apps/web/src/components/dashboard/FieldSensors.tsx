"use client";

import React, { useCallback, useEffect, useState } from "react";
import { fill, useI18n } from "@/i18n/I18nProvider";
import { sensorService, type SensorDevice, type SensorSnapshot } from "@/services/sensorService";

const POLL_MS = 5000; // the field unit sends a reading every 5 s
const STALE_S = 60; // no reading for a minute: show the values as "last known"

// Same moisture levels as the field unit (field-unit.ino: LOW_LEVEL 35, CRITICAL_LEVEL 20)
const LOW = 35;
const CRITICAL = 20;

type Tone = "good" | "warn" | "bad" | "muted";

// Text colours of the card variant (dashboard home).
const LIGHT_TEXT: Record<Tone, string> = { good: "text-[#c6f04a]", warn: "text-amber-300", bad: "text-[#ff7a70]", muted: "text-white/60" };

const TONE: Record<Tone, { text: string; ring: string; bg: string; bar: string }> = {
  good: { text: "text-[#c6f04a]", ring: "border-[#c6f04a]/35", bg: "bg-[#c6f04a]/[0.07]", bar: "bg-[#c6f04a]" },
  warn: { text: "text-amber-300", ring: "border-amber-400/35", bg: "bg-amber-400/[0.08]", bar: "bg-amber-400" },
  bad: { text: "text-red-300", ring: "border-red-400/40", bg: "bg-red-400/[0.09]", bar: "bg-red-400" },
  muted: { text: "text-neutral-300", ring: "border-white/10", bg: "bg-white/[0.03]", bar: "bg-neutral-500" },
};

/**
 * The field unit's live readings, in plain words. `cards` renders the same block as white cards, to sit with
 * the other cards of the dashboard home; the data and its source are unchanged.
 */
export function FieldSensors({ cards = false }: { cards?: boolean }) {
  const { m, locale } = useI18n();
  const t = m.sensors;
  const [snap, setSnap] = useState<SensorSnapshot | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    try {
      setSnap(await sensorService.latest());
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, POLL_MS);
    const onVisible = () => document.visibilityState === "visible" && void load();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [load]);

  const device: SensorDevice | undefined = snap?.devices.find((d) => d.latest) ?? snap?.devices[0];
  const r = device?.latest ?? null;
  const stale = !r || (device?.age_s ?? Infinity) > STALE_S;
  const fmt = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });

  // ---- connection line ----
  let link: { tone: Tone; text: string; pulse?: boolean };
  if (failed) link = { tone: "bad", text: t.linkApiDown };
  else if (!snap) link = { tone: "muted", text: t.linkLoading };
  else if (!r && device?.gateway === "offline") link = { tone: "warn", text: t.linkGatewayOff };
  else if (!r) link = { tone: "muted", text: t.linkWaiting };
  else if (stale) link = { tone: "warn", text: fill(t.linkStale, { ago: ago(device!.age_s!, t) }) };
  else link = { tone: "good", text: fill(t.linkLive, { ago: ago(device!.age_s!, t) }), pulse: true };

  // ---- the one-line answer ----
  let headline: { tone: Tone; title: string; text: string };
  if (!r) headline = { tone: "muted", title: t.noDataTitle, text: t.noDataText };
  else if (r.field_status === "sensor_fault") headline = { tone: "warn", title: t.faultTitle, text: t.faultText };
  else if (r.field_status === "critical") headline = { tone: "bad", title: t.criticalTitle, text: t.criticalText };
  else if (r.field_status === "low") headline = { tone: "warn", title: t.lowTitle, text: t.lowText };
  else headline = { tone: "good", title: t.goodTitle, text: t.goodText };
  if (r && stale) headline = { ...headline, tone: "muted" };

  const soil = r?.soil_moisture ?? null;
  const soilTone: Tone = soil == null ? "muted" : soil <= CRITICAL ? "bad" : soil <= LOW ? "warn" : "good";
  const light = r?.light ?? null;

  return (
    <section aria-label={t.title} className="space-y-4">
      {/* Title, connection line and the one-line answer (the dashboard home shows the four readings only) */}
      {!cards && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">{t.title}</h2>
            <p className={`inline-flex items-center gap-2 text-sm ${TONE[link.tone].text}`} role="status" aria-live="polite">
              <span className="relative flex w-2.5 h-2.5">
                {link.pulse && <span className={`absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping ${TONE[link.tone].bar}`} />}
                <span className={`relative inline-flex w-2.5 h-2.5 rounded-full ${TONE[link.tone].bar}`} />
              </span>
              {link.text}
            </p>
          </div>
          <div className={`rounded-2xl border p-5 sm:p-6 ${TONE[headline.tone].ring} ${TONE[headline.tone].bg}`}>
            <p className={`text-xl sm:text-2xl font-bold ${TONE[headline.tone].text}`}>{headline.title}</p>
            <p className="text-sm sm:text-base mt-1 text-neutral-300">{headline.text}</p>
          </div>
        </>
      )}

      {/* Four readings */}
      <div className={`grid grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4 ${stale && r ? "opacity-70" : ""}`}>
        <Tile
          cards={cards}
          icon={<IconSoil />}
          label={t.soil}
          value={soil == null ? null : `${soil}`}
          unit="%"
          tone={soilTone}
          hint={!r ? t.soilHint : soil == null ? t.soilMissing : soil <= CRITICAL ? t.soilVeryDry : soil <= LOW ? t.soilDry : t.soilOk}
          trend={device?.trend.soil_moisture ?? null}
          noData={t.noValue}
        >
          {soil != null && <SoilBar value={soil} tone={soilTone} />}
        </Tile>
        <Tile
          cards={cards}
          icon={<IconThermo />}
          label={t.temp}
          value={r?.air_temp == null ? null : fmt.format(r.air_temp)}
          unit="°C"
          hint={r && r.air_temp == null ? t.airMissing : t.tempHint}
          trend={device?.trend.air_temp ?? null}
          noData={t.noValue}
        />
        <Tile
          cards={cards}
          icon={<IconDropAir />}
          label={t.humidity}
          value={r?.air_humidity == null ? null : fmt.format(Math.round(r.air_humidity))}
          unit="%"
          hint={r && r.air_humidity == null ? t.airMissing : t.humidityHint}
          trend={device?.trend.air_humidity ?? null}
          noData={t.noValue}
        />
        <Tile
          cards={cards}
          icon={<IconSun />}
          label={t.light}
          value={light == null ? null : `${light}`}
          unit="%"
          hint={!r ? t.lightHint : light == null ? t.lightMissing : light < 20 ? t.lightDark : light < 60 ? t.lightShade : t.lightBright}
          trend={device?.trend.light ?? null}
          noData={t.noValue}
        />
      </div>
    </section>
  );
}

function ago(seconds: number, t: { secondsAgo: string; minutesAgo: string; hoursAgo: string }) {
  if (seconds < 60) return fill(t.secondsAgo, { n: Math.max(0, seconds) });
  if (seconds < 3600) return fill(t.minutesAgo, { n: Math.round(seconds / 60) });
  return fill(t.hoursAgo, { n: Math.round(seconds / 3600) });
}

type TileProps = {
  cards?: boolean;
  icon: React.ReactNode;
  label: string;
  value: string | null;
  unit: string;
  hint: string;
  tone?: Tone;
  trend: number | null;
  noData: string;
  children?: React.ReactNode;
};

function Tile({ cards = false, icon, label, value, unit, hint, tone = "muted", trend, noData, children }: TileProps) {
  const { m } = useI18n();
  const accent = value == null ? (cards ? "text-white/40" : "text-neutral-500") : tone === "muted" ? (cards ? "text-white" : "text-white") : cards ? LIGHT_TEXT[tone] : TONE[tone].text;
  return (
    <div className={cards ? "rounded-3xl bg-[#0d0f0c] border border-white/10 p-4 sm:p-5 flex flex-col gap-2 min-w-0 shadow-[0_10px_30px_rgba(0,0,0,0.18)] text-white" : "rounded-2xl border border-white/10 bg-white/[0.03] p-4 sm:p-5 flex flex-col gap-2 min-w-0"}>
      <div className={`flex items-start gap-2 min-h-[2.5rem] sm:min-h-0 ${cards ? "text-white/80" : "text-neutral-400"}`}>
        <span className={`text-xl ${cards ? "text-[#c6f04a]" : "text-neutral-300"}`}>{icon}</span>
        <span className="text-sm font-medium leading-tight">{label}</span>
      </div>
      <div className="flex items-end gap-1.5">
        {value == null ? (
          <span className={`text-2xl font-semibold ${cards ? "text-white/40" : "text-neutral-500"}`}>{noData}</span>
        ) : (
          <>
            <span className={`text-4xl sm:text-5xl font-bold tabular-nums leading-none ${accent}`}>{value}</span>
            <span className={`text-lg mb-0.5 ${cards ? "text-white/60" : "text-neutral-400"}`}>{unit}</span>
            <TrendArrow delta={trend} label={m.sensors.trendLabel} />
          </>
        )}
      </div>
      {children}
      <p className={`text-[13px] leading-snug ${cards ? "text-white/60" : "text-neutral-400"}`}>{hint}</p>
    </div>
  );
}

/** Small arrow when a value moved noticeably in the last minute; nothing when it is steady. */
function TrendArrow({ delta, label }: { delta: number | null; label: string }) {
  if (delta == null || Math.abs(delta) < 1) return null;
  const up = delta > 0;
  return (
    <span className="ms-auto self-start text-neutral-400 text-sm inline-flex items-center gap-0.5" title={label} aria-label={`${label}: ${up ? "+" : ""}${delta}`}>
      <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {up ? <path d="M6 10V2M2.5 5.5 6 2l3.5 3.5" /> : <path d="M6 2v8M2.5 6.5 6 10l3.5-3.5" />}
      </svg>
    </span>
  );
}

/** Moisture bar with the field unit's two levels marked (very dry under 20 %, dry under 35 %). */
function SoilBar({ value, tone }: { value: number; tone: Tone }) {
  return (
    <div className="relative h-2 rounded-full bg-white/10 overflow-hidden" aria-hidden="true">
      <div className={`absolute inset-y-0 start-0 rounded-full ${TONE[tone].bar}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      <span className="absolute inset-y-0 w-px bg-black/50" style={{ insetInlineStart: `${CRITICAL}%` }} />
      <span className="absolute inset-y-0 w-px bg-black/50" style={{ insetInlineStart: `${LOW}%` }} />
    </div>
  );
}

const svg = (d: string) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={d} />
  </svg>
);
const IconSoil = () => svg("M3 16h18M3 20h18M12 13V6m0 0c0-1.7 1.3-3 3-3 0 1.7-1.3 3-3 3Zm0 1c0-1.7-1.3-3-3-3 0 1.7 1.3 3 3 3Z");
const IconThermo = () => svg("M14 14.8V5a2 2 0 1 0-4 0v9.8a4 4 0 1 0 4 0ZM12 9v7");
const IconDropAir = () => svg("M12 3c3.5 4.2 6 7.6 6 10.6A6 6 0 0 1 6 13.6C6 10.6 8.5 7.2 12 3Zm-2.5 11a2.5 2.5 0 0 0 2.5 2.5");
const IconSun = () => svg("M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm0-4v1.5M12 19.5V21M3 12h1.5M19.5 12H21M5.6 5.6l1.1 1.1M17.3 17.3l1.1 1.1M5.6 18.4l1.1-1.1M17.3 6.7l1.1-1.1");
