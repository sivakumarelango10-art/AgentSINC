import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentSINC — SINC AI Office",
  description:
    "The SINC AI company office: coordinate specialist agents, tasks and collaboration in an original 3D workspace.",
  applicationName: "AgentSINC",
};

export const viewport: Viewport = {
  themeColor: "#080C17",
  width: "device-width",
  initialScale: 1,
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
