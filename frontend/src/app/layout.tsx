import type { Metadata, Viewport } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";
import { ThemeProvider, themeBootstrapScript } from "@/lib/theme";
import { I18nProvider } from "@/lib/i18n";
import { TelegramMiniAppBridge, telegramBootstrapScript } from "@/lib/telegram";

const pobeda = localFont({
  src: "../../public/fonts/pobeda-bold.ttf",
  variable: "--font-pobeda",
  weight: "700",
  style: "normal",
  display: "swap",
});

const arkhip = localFont({
  src: "../../public/fonts/arkhip.ttf",
  variable: "--font-arkhip",
  weight: "400",
  style: "normal",
  display: "swap",
});

const appetite = localFont({
  src: "../../public/fonts/appetite.ttf",
  variable: "--font-appetite",
  weight: "400",
  style: "normal",
  display: "swap",
});

const dmSans = DM_Sans({
  variable: "--font-body",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "PROpitashka — Персональный помощник по питанию и фитнесу",
  description: "Трекер питания, тренировок и воды с AI-ассистентом",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fcfaf6" },
    { media: "(prefers-color-scheme: dark)", color: "#11110f" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ru"
      className={`${pobeda.variable} ${arkhip.variable} ${appetite.variable} ${dmSans.variable} ${jetbrainsMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script src="https://telegram.org/js/telegram-web-app.js" async />
        <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />
        <script dangerouslySetInnerHTML={{ __html: telegramBootstrapScript }} />
      </head>
      <body className="min-h-full flex flex-col font-body">
        <ThemeProvider>
          <I18nProvider>
            <TelegramMiniAppBridge />
            {children}
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
