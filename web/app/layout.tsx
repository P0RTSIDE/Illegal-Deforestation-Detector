import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Deforestation Detector | Satellite + Permit Cross-Reference",
  description:
    "Portfolio project detecting land-cover change in the Brazilian Amazon and cross-referencing against public mining/logging concession data.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
