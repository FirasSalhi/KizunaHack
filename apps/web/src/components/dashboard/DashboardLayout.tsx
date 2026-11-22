"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n/I18nProvider";
import { LanguageSwitcher } from "@/i18n/LanguageSwitcher";
import { VoiceAssistant } from "@/components/assistant/VoiceAssistant";
import { getAssistant } from "@/components/assistant/farmAssistant";
import { IconClose, IconMenu, IconCrate, IconFields3D, IconMarketStall, IconOverview, IconSolarPanel, IconPlanMap, IconScanLeaf, IconSignOut } from "@/components/icons";

const NAV_ACTIVE = "flex items-center gap-3 px-3.5 py-3 rounded-xl bg-gradient-to-r from-[#3f9d2f] to-[#2d7a22] text-white font-semibold border border-[#8fd36a]/40 shadow-[0_4px_14px_rgba(60,160,40,0.35)]";
const NAV_IDLE = "flex items-center gap-3 px-3.5 py-3 rounded-xl text-[#dbe9d3] hover:text-white hover:bg-white/[0.07] border border-transparent transition-colors";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

/** Leaf logo of the design (sidebar). */
function LeafLogo() {
  return (
    <svg viewBox="0 0 48 48" width="44" height="44" aria-hidden="true">
      <defs>
        <linearGradient id="fl-leaf" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="#2f8f2a" />
          <stop offset="1" stopColor="#8fdc4e" />
        </linearGradient>
      </defs>
      <path d="M8 40C8 20 20 8 42 6c-1 22-13 34-32 34Z" fill="url(#fl-leaf)" />
      <path d="M10 38C18 28 26 20 36 13M19 29l-1-8M26 22l7 1" stroke="#0f3a16" strokeWidth="2" strokeLinecap="round" fill="none" opacity=".55" />
    </svg>
  );
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

  // Same routes as before; order and icons follow the dashboard design.
  const NAV = [
    { href: "/dashboard", label: t.nav.overview, icon: <IconOverview /> },
    { href: "/dashboard/irrigation-3d", label: t.nav.irrigation3d, icon: <IconFields3D /> },
    { href: "/dashboard/planning", label: t.nav.planning, icon: <IconPlanMap /> },
    { href: "/dashboard/scanner", label: t.nav.scanner, icon: <IconScanLeaf /> },
    { href: "/dashboard/solar", label: t.nav.solar, icon: <IconSolarPanel /> },
    { href: "/dashboard/market", label: t.nav.market, icon: <IconMarketStall /> },
    { href: "/dashboard/post-harvest", label: t.nav.postHarvest, icon: <IconCrate /> },
  ];

  return (
    <div className="min-h-screen bg-[#090b08] text-white flex flex-col lg:flex-row">
      {/* Sidebar for Desktop */}
      <aside className="hidden lg:flex w-[268px] flex-col justify-between bg-gradient-to-b from-[#123b1c] via-[#0e2f17] to-[#0a2111] border-e border-white/10 p-5 shrink-0 sticky top-0 h-screen">
        <div className="space-y-7">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-2.5 px-1">
            <LeafLogo />
            <div className="flex flex-col leading-tight">
              <span className="font-extrabold tracking-tight text-white text-[22px]">FARMLINK</span>
              <span className="text-[13px] text-[#a9e07a]">{t.tagline}</span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="space-y-1.5 text-[15px]">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} aria-current={pathname === n.href ? "page" : undefined} className={pathname === n.href ? NAV_ACTIVE : NAV_IDLE}>
                <span className="text-xl">{n.icon}</span>
                {n.label}
              </Link>
            ))}
          </nav>
        </div>

        {/* Assistant, language, user & logout */}
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => getAssistant().openListening()}
            className="w-full flex items-center gap-3 rounded-2xl border border-[#8fd36a]/35 bg-white/[0.04] px-4 py-3 text-white font-semibold hover:bg-white/[0.08]"
          >
            <span className="text-2xl"><IconBotSide /></span>
            {t.nav.assistant}
            <span className="ms-auto w-2.5 h-2.5 rounded-full bg-[#7ee04f] shadow-[0_0_8px_#7ee04f]" aria-hidden="true" />
          </button>
          <LanguageSwitcher placement="up" align="start" />
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#3f9d2f] text-white flex items-center justify-center font-bold uppercase">{user?.name?.[0] || "U"}</div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-white truncate">{user?.name || t.farmer}</div>
                <div className="text-[12px] text-[#b7c9ae] truncate">{user?.email}</div>
              </div>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] text-[#b7c9ae]">
              <span className="truncate">{primaryFarm} · {userRole}</span>
              <button onClick={() => void logout()} className="inline-flex items-center gap-1 text-[#dbe9d3] hover:text-red-300" title={m.common.signOut}>
                <IconSignOut /> <span className="sr-only">{m.common.signOut}</span>
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile Top Navigation */}
      <header className="lg:hidden flex items-center justify-between p-4 border-b border-white/10 bg-[#0e2f17]">
        <Link href="/dashboard" className="flex items-center gap-2 py-1.5">
          <LeafLogo />
          <span className="font-bold tracking-tight text-white text-base">FARMLINK</span>
        </Link>
        <LanguageSwitcher className="ms-auto me-2" />
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="w-11 h-11 grid place-items-center rounded-lg bg-white/5 text-neutral-200 text-xl"
          aria-label={t.toggleNav}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <IconClose /> : <IconMenu />}
        </button>
      </header>

      {/* Mobile drawer if open */}
      {mobileMenuOpen && (
        <div className="lg:hidden p-4 bg-[#0e2f17] border-b border-white/10 space-y-3">
          <div className="text-xs text-neutral-300 font-mono">{primaryFarm} ({userRole})</div>
          <nav className="flex flex-col divide-y divide-white/5">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} className={`block py-2.5 text-[15px] ${pathname === n.href ? "text-[#a9e07a]" : "text-neutral-200"}`}>
                {n.label}
              </Link>
            ))}
            <button type="button" onClick={() => void logout()} className="py-2.5 text-[15px] text-red-400 text-start">{m.common.signOut}</button>
          </nav>
        </div>
      )}

      {/* Voice assistant bubble (ported from the Pilo Tech "Horizon" assistant) */}
      <VoiceAssistant />

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}

function IconBotSide() {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v3m-6 3h12a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2Zm3 5h.01M15 14h.01M9.5 17h5M2 13v2M22 13v2" />
    </svg>
  );
}
