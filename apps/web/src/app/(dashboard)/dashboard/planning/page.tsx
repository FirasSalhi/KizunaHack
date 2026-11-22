"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { CropPlanner } from "@/components/dashboard/CropPlanner";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n/I18nProvider";

export default function PlanningPage() {
  const { user, isLoading } = useAuth();
  const { m } = useI18n();
  const router = useRouter();

  // Signed-out visitors (no account and no demo session) are sent to sign in.
  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [user, isLoading, router]);

  if (isLoading || !user) {
    return (
      <div className="min-h-screen bg-[#020302] flex items-center justify-center text-white">
        <div className="flex flex-col items-center gap-3">
          <span className="w-8 h-8 border-2 border-[#c6f04a] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-mono text-neutral-400">{m.dashboard.loading}</span>
        </div>
      </div>
    );
  }

  return (
    <DashboardLayout>
      <CropPlanner />
    </DashboardLayout>
  );
}
