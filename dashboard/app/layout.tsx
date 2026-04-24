import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HappyRobot Carrier Sales",
  description: "Inbound carrier sales agent performance dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-background">{children}</body>
    </html>
  );
}
