"use client";

import {
  config,
  Locale,
  LocaleLabel,
  useTranslation,
} from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";

import type { Icon } from "#components/icons";

import { Icons } from "#components/icons";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "#components/select";

export const LocaleIcon: Record<Locale, Icon> = {
  [Locale.EN]: Icons.UnitedKingdom,
  [Locale.SL]: Icons.Slovenia,
  [Locale.NB]: Icons.Norway,
} as const;

interface LocaleCustomizerProps {
  readonly onChange?: (lang: Locale) => Promise<void>;
  readonly variant?: "default" | "icon";
}

export const LocaleCustomizer = ({
  onChange,
  variant = "default",
}: LocaleCustomizerProps) => {
  const { i18n, t } = useTranslation("common");
  const locale = i18n.language as Locale;

  const handleLocaleChange = async (locale: Locale) => {
    await onChange?.(locale);
    await i18n.changeLanguage(locale);
  };

  const Icon = LocaleIcon[locale];

  return (
    <Select value={locale} onValueChange={handleLocaleChange}>
      <SelectTrigger
        className={cn({
          "w-full": variant === "default",
          "hover:bg-accent hover:text-accent-foreground flex size-10 items-center justify-center rounded-full border-none p-0 text-lg transition-colors [&>*:nth-child(2)]:hidden":
            variant === "icon",
        })}
        aria-label={t("language.change")}
      >
        {variant === "default" ? (
          <SelectValue aria-label={LocaleLabel[locale]} />
        ) : (
          <SelectValue aria-label={LocaleLabel[locale]}>
            <Icon className="size-10" />
          </SelectValue>
        )}
      </SelectTrigger>
      <SelectContent align="end">
        {config.locales.map((lang) => {
          const Icon = LocaleIcon[lang];

          return (
            <SelectItem key={lang} value={lang} className="cursor-pointer">
              <span className="flex items-center gap-2">
                <Icon className="size-4" />
                {LocaleLabel[lang]}
              </span>
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
};
