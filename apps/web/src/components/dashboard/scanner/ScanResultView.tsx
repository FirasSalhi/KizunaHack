"use client";

import React, { useEffect, useState } from "react";
import { IconChevronDown } from "@/components/icons";
import { fill, useI18n } from "@/i18n/I18nProvider";
import { plantService } from "@/services/plantService";
import type { DiseaseSheet, HealthStatus, PlantSearchHit, ScanResult, SpeciesSheet } from "@/types/plants";

export const HEALTH_TONE: Record<HealthStatus, { text: string; box: string; dot: string }> = {
  possible_disease: { text: "text-red-300", box: "border-red-400/30 bg-red-400/[0.07]", dot: "bg-red-400" },
  healthy_looking: { text: "text-[#c6f04a]", box: "border-[#c6f04a]/30 bg-[#c6f04a]/[0.06]", dot: "bg-[#c6f04a]" },
  uncertain: { text: "text-amber-300", box: "border-amber-400/30 bg-amber-400/[0.07]", dot: "bg-amber-400" },
  unavailable: { text: "text-neutral-400", box: "border-white/10 bg-white/[0.03]", dot: "bg-neutral-500" },
};

const pct = (x: number) => Math.round(x * 100);

type Props = {
  result: ScanResult;
  /** Called with the updated result after the user picked or confirmed the plant. */
  onChange: (next: ScanResult) => void;
};

/** Everything the scanner found for one photo (layout of is9ini's plant result view). */
export function ScanResultView({ result: r, onChange }: Props) {
  const { m } = useI18n();
  const t = m.scanner;
  const s = r.species;
  const [busy, setBusy] = useState(false);
  const [searching, setSearching] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function choose(speciesId: string) {
    setBusy(true);
    setErr(null);
    try {
      if (r.saved && r.scan_id) {
        const fixed = await plantService.fixScan(r.scan_id, speciesId);
        onChange({ ...fixed.result, saved: true, scan_id: r.scan_id });
      } else {
        const species: SpeciesSheet = await plantService.care(speciesId);
        onChange({ ...r, species, sure: true, chosen: true });
      }
      setSearching(false);
    } catch {
      setErr(t.errGeneric);
    } finally {
      setBusy(false);
    }
  }

  const leaf = r.leaf_health;
  const showLeaf = leaf.applicable && r.health.engine !== "PlantVillage leaf model (offline, beta)";

  return (
    <div className="space-y-5" aria-busy={busy}>
      {/* Header: name, family, confidence */}
      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 flex gap-5 items-start">
        <div className="flex-1 min-w-0">
          <span className="inline-block text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#c6f04a]/10 text-[#c6f04a] mb-2">{s.type}</span>
          <h2 className="text-2xl font-bold text-white leading-tight">{s.common_name}</h2>
          <p className="text-sm italic text-neutral-300 mt-0.5">{s.scientific_name}</p>
          {s.family && <p className="text-xs text-neutral-500 mt-1">{fill(t.family, { name: s.family })}</p>}
          {r.chosen && <p className="text-xs text-[#c6f04a] mt-2">{t.chosen}</p>}
        </div>
        <ScoreRing value={r.confidence} sure={r.sure} label={t.aiScore} />
      </section>

      {!r.sure && (
        <p className="rounded-xl border border-amber-400/30 bg-amber-400/[0.07] px-4 py-3 text-sm text-amber-100">
          {r.genus.sure && r.genus.name
            ? fill(t.probablyGenus, { genus: r.genus.name, pct: pct(r.genus.confidence) })
            : t.notSure}
        </p>
      )}

      <HealthCard result={r} />
      {showLeaf && <LeafCard leaf={leaf} />}

      {/* Alternatives and correction */}
      {(r.alternatives.length > 0 || !r.sure) && (
        <section className="space-y-3">
          {r.alternatives.length > 0 && (
            <>
              <SectionTitle>{r.sure ? t.couldAlsoBe : t.isItOne}</SectionTitle>
              <div className="flex flex-wrap gap-2">
                {r.alternatives.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    disabled={busy}
                    onClick={() => void choose(a.id)}
                    className="text-xs px-3 py-1.5 rounded-full border border-white/15 text-neutral-200 hover:border-[#c6f04a] hover:text-[#c6f04a] disabled:opacity-50"
                    title={a.scientific_name}
                  >
                    {a.common_name} <span className="text-neutral-500">{pct(a.confidence)}%</span>
                  </button>
                ))}
              </div>
            </>
          )}
          {!r.sure && (
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
              <p className="text-sm text-neutral-300">{fill(t.bestGuess, { name: s.common_name })}</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void choose(s.id)}
                  className="px-3 py-2 rounded-lg text-sm font-semibold bg-[#c6f04a] hover:bg-[#b5e03b] text-[#0d0f0c] disabled:opacity-50"
                >
                  {fill(t.confirm, { name: s.common_name })}
                </button>
                <button
                  type="button"
                  onClick={() => setSearching((v) => !v)}
                  className="px-3 py-2 rounded-lg text-sm border border-white/15 text-white hover:border-[#c6f04a]"
                >
                  {t.searchByName}
                </button>
              </div>
            </div>
          )}
          {r.sure && (
            <button type="button" onClick={() => setSearching((v) => !v)} className="text-xs text-neutral-400 hover:text-white underline underline-offset-4">
              {t.wrongPlant}
            </button>
          )}
          {searching && <PlantSearch busy={busy} onPick={(id) => void choose(id)} />}
          {err && <p role="alert" className="text-sm text-red-300">{err}</p>}
        </section>
      )}

      {/* Care sheet */}
      <section className="space-y-3">
        <SectionTitle>{r.sure ? t.careSheet : fill(t.careSheetGuess, { name: s.common_name })}</SectionTitle>
        {s.note && <p className="text-xs text-amber-200">{s.note}</p>}
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-2.5">
          {s.care.map((c) => (
            <div key={c.key} className="rounded-xl border border-white/10 bg-white/[0.03] p-3.5">
              <p className="text-xs text-neutral-500">{c.title}</p>
              <p className="font-semibold text-white mt-0.5">{c.value}</p>
              {c.detail && <p className="text-xs text-neutral-400 mt-0.5">{c.detail}</p>}
            </div>
          ))}
        </div>
        {s.sources.length > 0 && <p className="text-xs text-neutral-500">{fill(t.data, { sources: s.sources.join(" · ") })}</p>}
      </section>

      {s.recommended_settings && r.sure && (
        <section className="rounded-2xl border border-[#c6f04a]/20 bg-[#c6f04a]/[0.04] p-5">
          <SectionTitle>{t.settingsTitle}</SectionTitle>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <Stat value={`${s.recommended_settings.soil_dry_pct} %`} label={t.soilDry} />
            <Stat value={`${s.recommended_settings.soil_wet_pct} %`} label={t.soilWet} />
            <Stat
              value={`${s.recommended_settings.temp_min_c}–${s.recommended_settings.temp_max_c} °C`}
              label={t.tempRange}
            />
          </div>
          <p className="text-xs text-neutral-500 mt-3">{t.settingsNote}</p>
        </section>
      )}

      {s.possible_diseases.length > 0 && (
        <section className="space-y-2">
          <SectionTitle>{t.watchOut}</SectionTitle>
          {s.possible_diseases.map((d) => (
            <details key={d.id} className="group rounded-xl border border-white/10 bg-white/[0.02]">
              <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-white flex justify-between items-center">
                {d.name}
                <IconChevronDown className="text-neutral-500 group-open:rotate-180 transition-transform" />
              </summary>
              <div className="px-4 pb-4">
                <DiseaseBody d={d} />
              </div>
            </details>
          ))}
        </section>
      )}

      <p className="text-xs text-neutral-500 border-t border-white/10 pt-3">
        {fill(t.footer, { engine: r.engine, ms: r.ms })}
        {r.plantnet_remaining_today != null && ` · ${fill(t.plantnetLeft, { n: r.plantnet_remaining_today })}`}
      </p>
    </div>
  );
}

function HealthCard({ result: r }: { result: ScanResult }) {
  const { m } = useI18n();
  const t = m.scanner;
  const h = r.health;
  const tone = HEALTH_TONE[h.status] ?? HEALTH_TONE.unavailable;
  const title =
    h.status === "possible_disease" ? fill(t.healthSick, { name: h.top?.name ?? "" })
      : h.status === "healthy_looking" ? t.healthOk
      : h.status === "uncertain" ? t.healthUnsure
      : t.healthNa;
  const sheet = h.top?.sheet;
  return (
    <section className={`rounded-2xl border p-5 space-y-2 ${tone.box}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold tracking-[0.14em] text-neutral-500">{t.healthLabel}</p>
          <p className={`text-base font-bold ${tone.text}`}>{title}</p>
        </div>
        {h.confidence != null && (
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full border border-current ${tone.text}`}>{pct(h.confidence)}%</span>
        )}
      </div>
      <p className="text-sm text-neutral-200">{h.message}</p>
      {h.top?.scientific && <p className="text-xs italic text-neutral-400">{h.top.scientific}</p>}
      {h.status === "possible_disease" && sheet && (
        <details className="rounded-lg bg-black/20 border border-white/10">
          <summary className="cursor-pointer px-3 py-2 text-sm text-white">{t.treatment}</summary>
          <div className="px-3 pb-3">
            <DiseaseBody d={sheet} />
          </div>
        </details>
      )}
      {h.others.length > 0 && (
        <p className="text-xs text-neutral-400">
          {fill(t.healthOthers, { list: h.others.map((o) => `${o.name} ${pct(o.score)}%`).join(" · ") })}
        </p>
      )}
      <p className="text-[11px] text-neutral-500">{fill(t.healthFoot, { engine: h.engine ?? t.noEngine })}</p>
    </section>
  );
}

function LeafCard({ leaf }: { leaf: ScanResult["leaf_health"] }) {
  const { m } = useI18n();
  const t = m.scanner;
  const title = !leaf.sure
    ? t.leafUnsure
    : leaf.healthy
      ? t.leafHealthy
      : fill(t.leafPossible, { name: leaf.disease?.name ?? leaf.label ?? "" });
  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-1">
      <div className="flex items-center gap-2">
        <p className="text-sm font-semibold text-white flex-1">{title}</p>
        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-400/15 text-amber-300">BETA</span>
      </div>
      {leaf.label && (
        <p className="text-xs text-neutral-400">{fill(t.closest, { label: leaf.label, pct: pct(leaf.confidence ?? 0) })}</p>
      )}
      {leaf.note && <p className="text-[11px] italic text-neutral-500">{leaf.note}</p>}
    </section>
  );
}

function DiseaseBody({ d }: { d: DiseaseSheet }) {
  const { m } = useI18n();
  const t = m.scanner;
  return (
    <div className="space-y-2 text-sm">
      <div>
        <p className="text-xs font-semibold text-[#c6f04a]">{t.symptoms}</p>
        <p className="text-neutral-300">{d.symptoms}</p>
      </div>
      <div>
        <p className="text-xs font-semibold text-[#c6f04a]">{t.prevention}</p>
        <p className="text-neutral-300">{d.prevention}</p>
      </div>
      {d.treatment.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-[#c6f04a]">{t.treatment}</p>
          <ol className="mt-1 space-y-1">
            {d.treatment.map((step, i) => (
              <li key={i} className="flex gap-2 text-neutral-300">
                <span className="shrink-0 w-5 h-5 rounded-full bg-[#c6f04a]/15 text-[#c6f04a] text-[10px] font-bold grid place-items-center">{i + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function PlantSearch({ busy, onPick }: { busy: boolean; onPick: (id: string) => void }) {
  const { m } = useI18n();
  const t = m.scanner;
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<PlantSearchHit[] | null>(null);

  useEffect(() => {
    if (q.trim().length < 2) {
      setHits(null);
      return;
    }
    let alive = true;
    const timer = setTimeout(() => {
      plantService
        .search(q.trim())
        .then((rows) => alive && setHits(rows))
        .catch(() => alive && setHits([]));
    }, 250);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [q]);

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 space-y-2">
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t.searchPh}
        aria-label={t.searchByName}
        className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2 text-sm text-white placeholder:text-neutral-500 focus:outline-none focus:border-[#c6f04a]/60"
      />
      {hits && hits.length === 0 && <p className="text-xs text-neutral-500 px-1">{t.noHits}</p>}
      {hits && hits.length > 0 && (
        <ul className="max-h-60 overflow-y-auto">
          {hits.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                disabled={busy}
                onClick={() => onPick(h.id)}
                className="w-full text-start px-2 py-1.5 rounded-md hover:bg-white/5 disabled:opacity-50"
              >
                <span className="block text-sm text-white">{h.common_name}</span>
                <span className="block text-xs italic text-neutral-500">{h.scientific_name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ScoreRing({ value, sure, label }: { value: number; sure: boolean; label: string }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const color = sure ? "#c6f04a" : "#fbbf24";
  return (
    <div className="relative w-[72px] h-[72px] shrink-0" role="img" aria-label={`${label}: ${pct(value)}%`}>
      <svg viewBox="0 0 64 64" className="w-full h-full -rotate-90" aria-hidden="true">
        <circle cx="32" cy="32" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
        <circle cx="32" cy="32" r={r} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" strokeDasharray={`${c * value} ${c}`} />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <p className="text-base font-bold leading-none" style={{ color }}>{pct(value)}%</p>
          <p className="text-[9px] text-neutral-500 mt-0.5">{label}</p>
        </div>
      </div>
    </div>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl bg-black/20 border border-white/10 p-3 text-center">
      <p className="text-lg font-bold text-white">{value}</p>
      <p className="text-[11px] text-neutral-400">{label}</p>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-white">{children}</h3>;
}
