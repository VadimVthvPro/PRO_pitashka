import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono } from "next/font/google";
import localFont from "next/font/local";
import "./globals.css";

// --- Custom display fonts ---
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

// --- Body & Mono ---
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ru"
      className={`${pobeda.variable} ${arkhip.variable} ${appetite.variable} ${dmSans.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-body">{children}</body>
    </html>
  );
}
