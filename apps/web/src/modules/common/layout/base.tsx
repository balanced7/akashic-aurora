import { Geist_Mono, Poppins } from "next/font/google";

import { cn } from "@akashic-labs/ui";

import { appConfig } from "~/config/app";

const sans = Poppins({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
  weight: ["300", "400", "500", "600", "700", "800"],
});

const mono = Geist_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
  weight: ["300", "400", "500"],
});

interface BaseLayoutProps {
  readonly locale: string;
  readonly children: React.ReactNode;
}

export const BaseLayout = ({ children, locale }: BaseLayoutProps) => {
  return (
    // next-themes sets the theme class and color-scheme on <html> before hydration.
    <html
      lang={locale}
      className={cn(sans.variable, mono.variable)}
      suppressHydrationWarning
    >
      <body
        suppressHydrationWarning
        className={cn(
          "bg-background text-foreground flex min-h-screen flex-col items-center justify-center font-sans antialiased",
          `theme-${appConfig.theme.color}`,
        )}
      >
        {children}
      </body>
    </html>
  );
};
