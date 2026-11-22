"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n/I18nProvider";
import { LanguageSwitcher } from "@/i18n/LanguageSwitcher";
import { BrandMark, IconCrate, IconFields3D, IconOverview, IconPlanMap, IconSignOut } from "@/components/icons";

const NAV_ACTIVE = "flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#c6f04a]/15 text-[#c6f04a] font-medium border border-[#c6f04a]/20";
const NAV_IDLE = "flex items-center gap-3 px-3 py-2.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5 border border-transparent transition-colors";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { user, logout } = useAuth();
  const { m } = useI18n();
  const t = m.dashboard;
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const primaryFarm = user?.memberships?.[0]?.farm_name || "Mornag Smart Farm";
  const roleKey = (user?.memberships?.[0]?.role || "owner") as keyof typeof t.roles;
  const userRole = t.roles[roleKey] ?? roleKey;

  return (
    <div className="min-h-screen bg-[#090b08] text-white flex flex-col lg:flex-row">
      {/* Sidebar for Desktop */}
      <aside className="hidden lg:flex w-64 flex-col justify-between border-e border-white/10 bg-[#0d100d] p-6 shrink-0">
        <div className="space-y-8">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-3">
            <span className="w-9 h-9 rounded-xl bg-[#c6f04a] text-[#0d0f0c] font-bold flex items-center justify-center text-lg shadow-[0_0_15px_rgba(198,240,74,0.3)]">
              <BrandMark />
            </span>
            <div className="flex flex-col">
              <span className="font-bold tracking-tight text-white text-base">FARMLINK</span>
              <span className="text-[10px] text-[#c6f04a] tracking-widest font-mono uppercase">ROOTLOOP SYSTEM</span>
            </div>
          </Link>

          {/* Farm Switcher Card */}
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="text-[10px] uppercase font-mono text-neutral-400">{t.activeProperty}</div>
            <div className="text-sm font-semibold text-white truncate mt-0.5">{primaryFarm}</div>
            <div className="flex items-center gap-1.5 mt-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-emerald-400 font-mono capitalize">{userRole}</span>
              <span className="text-neutral-600 text-xs">•</span>
              <span className="text-xs text-neutral-400 font-mono">{t.sensorsLive}</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5 text-sm">
            <Link
              href="/dashboard"
              aria-current={pathname === "/dashboard" ? "page" : undefined}
              className={pathname === "/dashboard" ? NAV_ACTIVE : NAV_IDLE}
            >
              <span className="text-base"><IconOverview /></span>
              {t.nav.overview}
            </Link>
            <Link
              href="/dashboard/planning"
              aria-current={pathname === "/dashboard/planning" ? "page" : undefined}
              className={pathname === "/dashboard/planning" ? NAV_ACTIVE : NAV_IDLE}
            >
              <span className="text-base"><IconPlanMap /></span>
              {t.nav.planning}
            </Link>
            <Link
              href="/dashboard/post-harvest"
              aria-current={pathname === "/dashboard/post-harvest" ? "page" : undefined}
              className={pathname === "/dashboard/post-harvest" ? NAV_ACTIVE : NAV_IDLE}
            >
              <span className="text-base"><IconCrate /></span>
              {t.nav.postHarvest}
            </Link>
            <Link
              href="/dashboard/irrigation-3d"
              aria-current={pathname === "/dashboard/irrigation-3d" ? "page" : undefined}
              className={pathname === "/dashboard/irrigation-3d" ? NAV_ACTIVE : NAV_IDLE}
            >
              <span className="text-base"><IconFields3D /></span>
              {t.nav.irrigation3d}
            </Link>
          </nav>
        </div>

        {/* User profile & Logout */}
        <div className="pt-6 border-t border-white/10 space-y-3">
          <LanguageSwitcher placement="up" align="start" />
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#17622a] text-white flex items-center justify-center font-bold text-xs uppercase">
              {user?.name?.[0] || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-white truncate">{user?.name || t.farmer}</div>
              <div className="text-[11px] text-neutral-400 truncate">{user?.email}</div>
            </div>
          </div>
          <button
            onClick={() => void logout()}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs text-neutral-400 hover:text-red-400 hover:bg-red-950/30 border border-white/5 transition-colors"
          >
            <span className="text-base"><IconSignOut /></span> {m.common.signOut}
          </button>
        </div>
      </aside>

      {/* Mobile Top Navigation */}
      <header className="lg:hidden flex items-center justify-between p-4 border-b border-white/10 bg-[#0d100d]">
        <Link href="/dashboard" className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-[#c6f04a] text-[#0d0f0c] font-bold flex items-center justify-center text-sm">
            <BrandMark />
          </span>
          <span className="font-bold tracking-tight text-white text-sm">FARMLINK</span>
        </Link>
        <LanguageSwitcher className="ms-auto me-2" />
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg bg-white/5 text-neutral-300"
          aria-label={t.toggleNav}
        >
          {mobileMenuOpen ? "✕" : "☰"}
        </button>
      </header>

      {/* Mobile drawer if open */}
      {mobileMenuOpen && (
        <div className="lg:hidden p-4 bg-[#0d100d] border-b border-white/10 space-y-3">
          <div className="text-xs text-neutral-400 font-mono">{primaryFarm} ({userRole})</div>
          <nav className="flex flex-col gap-2">
            <Link href="/dashboard" className={`text-sm ${pathname === "/dashboard" ? "text-[#c6f04a]" : "text-neutral-300"}`}>{t.nav.overview}</Link>
            <Link href="/dashboard/planning" className={`text-sm ${pathname === "/dashboard/planning" ? "text-[#c6f04a]" : "text-neutral-300"}`}>{t.nav.planning}</Link>
            <Link href="/dashboard/post-harvest" className={`text-sm ${pathname === "/dashboard/post-harvest" ? "text-[#c6f04a]" : "text-neutral-300"}`}>{t.nav.postHarvest}</Link>
            <Link href="/dashboard/irrigation-3d" className={`text-sm ${pathname === "/dashboard/irrigation-3d" ? "text-[#c6f04a]" : "text-neutral-300"}`}>{t.nav.irrigation3d}</Link>
            <button onClick={() => void logout()} className="text-sm text-red-400 text-start">{m.common.signOut}</button>
          </nav>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
