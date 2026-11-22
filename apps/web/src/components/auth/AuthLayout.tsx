"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { BrandMark } from "@/components/icons";
import { useI18n } from "@/i18n/I18nProvider";
import { LanguageSwitcher } from "@/i18n/LanguageSwitcher";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
  alternateLink?: {
    text: string;
    href: string;
    actionText: string;
  };
}

export function AuthLayout({
  children,
  title,
  subtitle,
  alternateLink,
}: AuthLayoutProps) {
  const { user, isLoading } = useAuth();
  const { m } = useI18n();
  const router = useRouter();

  // If already authenticated, redirect straight to the dashboard
  useEffect(() => {
    if (!isLoading && user) router.replace("/dashboard");
  }, [isLoading, user, router]);

  return (
    <div className="min-h-screen w-full flex bg-[#0c0f0d] text-neutral-100 font-sans antialiased">
      {/* Left side: Editorial photography showcasing real agriculture */}
      <div className="hidden lg:relative lg:flex lg:w-1/2 flex-col justify-between p-12 overflow-hidden border-e border-[#1e2520]">
        {/* Full-bleed background photograph */}
        <Image
          src="/images/farmlink-field-aerial.jpg"
          alt={m.auth.panelAlt}
          fill
          priority
          sizes="50vw"
          className="object-cover object-center"
        />

        {/* Natural dark vignette overlay to ensure pristine text readability */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0c0f0d] via-[#0c0f0d]/50 to-[#0c0f0d]/40" />

        {/* Brand header */}
        <header className="relative z-10">
          <Link href="/" className="inline-flex items-center gap-2.5 group">
            <span className="w-8 h-8 rounded-lg bg-[#a3e635] text-[#0c0f0d] font-bold flex items-center justify-center text-base transition-transform group-hover:scale-105">
              <BrandMark />
            </span>
            <span className="font-semibold tracking-tight text-white text-lg">
              FARMLINK
            </span>
          </Link>
        </header>

        {/* Editorial customer testimonial */}
        <footer className="relative z-10 max-w-lg space-y-4">
          <blockquote className="text-xl font-medium text-white/95 leading-relaxed">
            &ldquo;{m.auth.quote}&rdquo;
          </blockquote>
          <div className="flex items-center gap-3 pt-1">
            <div className="w-9 h-9 rounded-full bg-[#1b251d] border border-[#2e3e31] flex items-center justify-center text-xs font-semibold text-[#a3e635]">
              MT
            </div>
            <div>
              <div className="text-sm font-semibold text-white">Mohamed Trabelsi</div>
              <div className="text-xs text-neutral-400">{m.auth.quoteRole}</div>
            </div>
          </div>
        </footer>
      </div>

      {/* Right side: Clean, solid, human-centered form container */}
      <div className="w-full lg:w-1/2 flex flex-col justify-between p-6 sm:p-12 relative overflow-y-auto bg-[#0c0f0d]">
        {/* Top bar with back to home and alternate auth action */}
        <nav className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 w-full max-w-md mx-auto mb-8 text-xs text-neutral-400">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 hover:text-white transition-colors"
          >
            <span aria-hidden="true" className="flip-rtl">&larr;</span> {m.auth.backHome}
          </Link>

          <LanguageSwitcher />
          {alternateLink && (
            <div className="flex items-center gap-1.5">
              <span>{alternateLink.text}</span>
              <Link
                href={alternateLink.href}
                className="font-medium text-[#a3e635] hover:underline"
              >
                {alternateLink.actionText}
              </Link>
            </div>
          )}
        </nav>

        {/* Solid, crisp card */}
        <main className="w-full max-w-md mx-auto my-auto">
          <div className="bg-[#141815] border border-[#222a23] rounded-2xl p-6 sm:p-8 shadow-2xl">
            <header className="mb-6">
              <h1 className="text-2xl font-bold text-white tracking-tight">{title}</h1>
              <p className="text-sm text-neutral-400 mt-1.5">{subtitle}</p>
            </header>

            {children}
          </div>
        </main>

        {/* Bottom subtle copyright */}
        <footer className="w-full max-w-md mx-auto mt-8 pt-4 text-center text-xs text-neutral-500">
          {m.auth.footer}
        </footer>
      </div>
    </div>
  );
}
