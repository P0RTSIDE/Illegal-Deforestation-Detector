import type { Metadata } from "next";
import { Source_Sans_3 } from "next/font/google";
import "./globals.css";

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Forest Clearing and Permit Map | Brazilian Amazon",
  description:
    "Satellite-detected vegetation loss cross-referenced against public mining and logging permit records in the Brazilian Amazon.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={sourceSans.className}>{children}</body>
    </html>
  );
}
