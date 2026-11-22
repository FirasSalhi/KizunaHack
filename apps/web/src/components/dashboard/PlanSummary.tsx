"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { fill, useI18n } from "@/i18n/I18nProvider";
import { clearPlan, loadPlan, PLAN_EVENT, PLAN_KEY, type FarmPlan } from "@/lib/farmPlan";

/** The validated plan, kept in sync across pages and tabs. */
export function useFarmPlan(): FarmPlan | null {
  const [plan, setPlan] = useState<FarmPlan | null>(null);
  useEffect(() => {
    const update = () => setPlan(loadPlan());
    update();
    const onStorage = (e: StorageEvent) => e.key === PLAN_KEY && update();
    window.addEventListener(PLAN_EVENT, update);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(PLAN_EVENT, update);
      window.removeEventListener("storage", onStorage);
    };
  }, []);
  return plan;
}

type Props = {
  /** planner: after validation, with links onward; tool: in Irrigation 3D / Post-Harvest, with a link back */
  variant: "planner" | "tool";
  /** for the tool variant: does this tool use the plan's crops? (Post-Harvest only stores some crops) */
  usable?: boolean;
};

/** One line saying which crops the farmer validated, so they are never chosen twice. */
export function PlanSummary({ variant, usable = true }: Props) {
  const { m, locale } = useI18n();
  const t = m.farmPlan;
  const plan = useFarmPlan();
  const ha = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });

  if (!plan) {
    if (variant === "planner") return null;
    return (
      <p className="text-xs text-neutral-400 mt-2">
        {t.noneText}{" "}
        <Link href="/dashboard/planning" className="inline-block py-1 text-[#c6f04a] underline underline-offset-4">
          {t.goPlanning}
        </Link>
      </p>
    );
  }

  const crops = plan.crops.map((c) => `${c.name} ${ha.format(c.area_ha)} ha`).join(" · ");
  return (
    <div className="mt-3 rounded-xl border border-[#c6f04a]/30 bg-[#c6f04a]/[0.06] px-4 py-3 text-sm" role="status">
      <p className="text-white">
        <span className="font-semibold text-[#c6f04a]">{variant === "planner" ? t.validated : t.fromPlan}</span>{" "}
        {crops}
        <span className="text-neutral-400"> · {fill(t.total, { area: ha.format(plan.area_ha) })}</span>
      </p>
      {variant === "tool" && !usable && <p className="text-xs text-amber-200 mt-1">{t.notStored}</p>}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-xs">
        {variant === "planner" ? (
          <>
            <Link href="/dashboard/irrigation-3d" className="py-1 text-[#c6f04a] underline underline-offset-4">{t.openIrrigation}</Link>
            <Link href="/dashboard/post-harvest" className="py-1 text-[#c6f04a] underline underline-offset-4">{t.openPostHarvest}</Link>
            <button type="button" onClick={clearPlan} className="py-1 text-neutral-400 hover:text-white underline underline-offset-4">
              {t.clear}
            </button>
          </>
        ) : (
          <Link href="/dashboard/planning" className="py-1 text-neutral-300 hover:text-white underline underline-offset-4">{t.change}</Link>
        )}
      </div>
    </div>
  );
}
