import type { Metadata, Viewport } from "next";
import { cookies, headers } from "next/headers";
import { dirOf, LOCALE_COOKIE, resolveLocale } from "@/i18n/config";
import "./globals.css";
import { Providers } from "./providers";

// Offline-resilient font fallback using DM Sans and system-ui font stack
const dmSans = { variable: "font-sans" };

export const metadata: Metadata = {
  title: "Mdhalla — Precision Agriculture",
  description:
    "Mdhalla combines AI vision, sensors and precision action to protect crops with less water, fewer chemicals and lower costs.",
  applicationName: "Mdhalla",
  // Installed on an iPhone: opens full-screen with the Mdhalla name and icon (the manifest is app/manifest.ts).
  appleWebApp: { capable: true, title: "Mdhalla", statusBarStyle: "black" },
  formatDetection: { telephone: false },
  icons: {
    icon: [
      { url: "/icons/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export const viewport: Viewport = {
  // Colour of the phone's status bar and the installed app's title bar.
  themeColor: "#020302",
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
