import type { Metadata } from "next";
import { cookies, headers } from "next/headers";
import { dirOf, LOCALE_COOKIE, resolveLocale } from "@/i18n/config";
import "./globals.css";
import { Providers } from "./providers";

// Offline-resilient font fallback using DM Sans and system-ui font stack
const dmSans = { variable: "font-sans" };

export const metadata: Metadata = {
  title: "FARMLINK — Precision Agriculture",
  description:
    "FARMLINK combines AI vision, sensors and precision action to protect crops with less water, fewer chemicals and lower costs.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Saved language (cookie), else the browser's preference, else French. Rendered server-side, so the
  // first paint is already in the right language and direction.
  const locale = resolveLocale((await cookies()).get(LOCALE_COOKIE)?.value, (await headers()).get("accept-language"));
  return (
    <html lang={locale} dir={dirOf(locale)} className={dmSans.variable}>
      {/* Browser extensions add attributes to <body>; don't treat that as a hydration error. */}
      <body suppressHydrationWarning>
        <Providers locale={locale}>{children}</Providers>
      </body>
    </html>
  );
}
