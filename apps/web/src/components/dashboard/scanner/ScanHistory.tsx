"use client";

import React, { useEffect, useState } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { IconClose } from "@/components/icons";
import { plantService } from "@/services/plantService";
import type { ScanSummary } from "@/types/plants";
import { HEALTH_TONE } from "./ScanResultView";

type Props = {
  /** Changes whenever a scan was added or corrected, to reload the list. */
  refreshKey: number;
  activeId?: string;
  onOpen: (id: string) => void;
  onDeleted: (id: string) => void;
};

/** The signed-in user's saved scans, newest first. */
export function ScanHistory({ refreshKey, activeId, onOpen, onDeleted }: Props) {
  const { m, locale } = useI18n();
  const t = m.scanner;
  const [scans, setScans] = useState<ScanSummary[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    plantService
      .listScans()
      .then((rows) => alive && (setScans(rows), setFailed(false)))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [refreshKey]);

  async function remove(id: string) {
    if (!window.confirm(t.deleteConfirm)) return;
    try {
      await plantService.deleteScan(id);
      setScans((rows) => rows?.filter((s) => s.id !== id) ?? null);
      onDeleted(id);
    } catch {
      setFailed(true);
    }
  }

  const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });

  return (
    <section className="rounded-xl border border-white/10 bg-white/[0.02]">
      <h2 className="px-4 pt-4 pb-2 text-xs font-mono uppercase tracking-wider text-neutral-500">{t.history}</h2>
      {failed && <p className="px-4 pb-3 text-xs text-red-300">{t.historyError}</p>}
      {scans && scans.length === 0 && <p className="px-4 pb-4 text-sm text-neutral-500">{t.historyEmpty}</p>}
      <ul className="max-h-[360px] overflow-y-auto">
        {scans?.map((s) => (
          <li key={s.id} className={`flex items-center gap-3 px-4 py-2.5 border-t border-white/5 ${activeId === s.id ? "bg-[#c6f04a]/5" : ""}`}>
            <Thumb id={s.id} />
            <button type="button" onClick={() => onOpen(s.id)} className="flex-1 min-w-0 text-start group">
              <span className="block text-sm font-medium text-white truncate group-hover:text-[#c6f04a]">{s.common_name}</span>
              <span className="block text-xs text-neutral-500 truncate">
                <i>{s.scientific_name}</i> · {Math.round(s.confidence * 100)}% · {date.format(new Date(s.created_at))}
              </span>
            </button>
            {s.health_status && s.health_status !== "unavailable" && (
              <span className={`w-2 h-2 rounded-full shrink-0 ${HEALTH_TONE[s.health_status].dot}`} aria-hidden="true" />
            )}
            <button
              type="button"
              onClick={() => void remove(s.id)}
              className="text-xs text-neutral-500 hover:text-red-300 px-1"
              aria-label={`${t.delete}: ${s.common_name}`}
            >
              <IconClose />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Thumb({ id }: { id: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let current: string | null = null;
    let alive = true;
    void plantService.photoUrl(id).then((u) => {
      current = u;
      if (alive) setUrl(u);
      else if (u) URL.revokeObjectURL(u);
    });
    return () => {
      alive = false;
      if (current) URL.revokeObjectURL(current);
    };
  }, [id]);
  return url ? (
    // eslint-disable-next-line @next/next/no-img-element -- authenticated object URL
    <img src={url} alt="" className="w-10 h-10 rounded-lg object-cover shrink-0" />
  ) : (
    <span className="w-10 h-10 rounded-lg bg-white/5 shrink-0" />
  );
}
