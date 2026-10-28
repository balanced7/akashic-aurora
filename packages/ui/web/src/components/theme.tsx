"use client";

import * as React from "react";
import { memo } from "react";
import { useTranslation } from "react-i18next";

import { ThemeColor, ThemeMode } from "@akashic-labs/ui";
import { cn } from "@akashic-labs/ui";

import type { ThemeConfig } from "@akashic-labs/ui";

import { Button } from "#components/button";
import { Icons } from "#components/icons";
import { Label } from "#components/label";

interface ThemeCustomizerProps {
  readonly config: ThemeConfig;
  readonly defaultConfig?: ThemeConfig;
  readonly onChange: (config: ThemeConfig) => void;
}

const MODE_ICONS = {
  [ThemeMode.LIGHT]: Icons.Sun,
  [ThemeMode.DARK]: Icons.Moon,
  [ThemeMode.SYSTEM]: Icons.SunMoon,
} as const;

export const ThemeCustomizer = memo<ThemeCustomizerProps>(
  ({ config, onChange }) => {
    const { t } = useTranslation("common");

    return (
      <div className="flex flex-1 flex-col items-center space-y-4 md:space-y-6">
        <div className="w-full space-y-1.5">
          <Label className="text-xs">{t("theme.color.label")}</Label>
          <div className="grid grid-cols-3 gap-2">
            {Object.values(ThemeColor)
              .filter((color) => Object.values(ThemeColor).includes(color))
              .map((color) => {
                const isActive = config.color === color;

                return (
                  <Button
                    variant="outline"
                    size="sm"
                    key={color}
                    onClick={() => onChange({ ...config, color })}
                    className={cn(
                      "justify-start gap-2 text-xs capitalize",
                      isActive && "border-primary dark:border-primary border-2",
                    )}
                  >
                    <span
                      className={cn(
                        "bg-primary flex size-4 shrink-0 items-center justify-center rounded-full",
                        `theme-${color}`,
                      )}
                    ></span>
                    {t(`theme.color.${color}`)}
                  </Button>
                );
              })}
          </div>
        </div>
        <div className="w-full space-y-1.5">
          <Label className="text-xs">{t("theme.mode.label")}</Label>
          <div className="grid grid-cols-3 gap-2">
            {Object.values(ThemeMode).map((mode) => {
              const isActive = config.mode === mode;
              const Icon = MODE_ICONS[mode];

              return (
                <Button
                  variant="outline"
                  key={mode}
                  size="sm"
                  onClick={() => onChange({ ...config, mode })}
                  className={cn(
                    "justify-start gap-2 text-xs capitalize",
                    isActive && "border-primary dark:border-primary border-2",
                  )}
                >
                  <Icon className="size-4 shrink-0" />
                  {t(`theme.mode.${mode}`)}
                </Button>
              );
            })}
          </div>
        </div>
      </div>
    );
  },
);

ThemeCustomizer.displayName = "ThemeCustomizer";
