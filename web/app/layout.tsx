import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WC2026 Simulation Console",
  description:
    "Constrained forecasting console — Monte Carlo outcomes + narrative simulation for the 2026 World Cup.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
