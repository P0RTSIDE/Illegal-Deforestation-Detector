import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Forest Clearing & Permit Map | Brazilian Amazon",
  description:
    "Satellite-detected vegetation loss cross-referenced against public mining permit records in the Brazilian Amazon.",
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
