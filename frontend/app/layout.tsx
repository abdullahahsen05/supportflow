import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SupportFlow AI",
  description: "CloudDesk Customer Support",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
