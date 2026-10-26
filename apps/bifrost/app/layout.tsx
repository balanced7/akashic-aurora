import type { Metadata, Viewport } from "next";
import { Toaster } from "sonner";

import "./globals.css";

export const metadata: Metadata = {
  title: "Bifrost: Live Agent Console",
  description: "Watch and steer live agent collaboration on the Bifrost bus.",
};

export const viewport: Viewport = { themeColor: "#0a0b0f", colorScheme: "dark" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        {children}
        <Toaster theme="dark" position="bottom-center" offset={110} richColors closeButton />
      </body>
    </html>
  );
}
