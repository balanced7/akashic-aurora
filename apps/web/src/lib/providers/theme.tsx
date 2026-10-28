"use client";

import { ThemeProvider as NextThemeProvider } from "next-themes";
import { memo, useEffect } from "react";
import { create } from "zustand";
import { persist } from "zustand/middleware";

import { appConfig } from "~/config/app";

import type { ThemeConfig } from "@akashic-labs/ui";

export const useThemeConfig = create<{
  config: Omit<ThemeConfig, "mode">;
  setConfig: (config: Omit<ThemeConfig, "mode">) => void;
}>()(
  persist(
    (set) => ({
      config: appConfig.theme,
      setConfig: (config) => set({ config }),
    }),
    {
      name: "theme-config",
    },
  ),
);

interface ThemeProviderProps {
  readonly children: React.ReactNode;
}

const ThemeConfigProvider = () => {
  const themeConfig = useThemeConfig((s) => s.config);

  useEffect(() => {
    Array.from(document.body.classList)
      .filter((className) => className.startsWith("theme-"))
      .forEach((className) => {
        document.body.classList.remove(className);
      });

    document.body.classList.add(`theme-${themeConfig.color}`);
  }, [themeConfig.color]);

  return null;
};

export const ThemeProvider = memo<ThemeProviderProps>(({ children }) => {
  return (
    <NextThemeProvider
      attribute="class"
      defaultTheme={appConfig.theme.mode}
      enableSystem
      disableTransitionOnChange
    >
      {children}
      <ThemeConfigProvider />
    </NextThemeProvider>
  );
});

ThemeProvider.displayName = "ThemeProvider";
