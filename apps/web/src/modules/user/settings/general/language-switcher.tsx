"use client";

import { useTranslation } from "@akashic-labs/i18n";

import { I18nControls } from "~/modules/common/i18n/controls";
import {
  SettingsCard,
  SettingsCardContent,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";

export const LanguageSwitcher = () => {
  const { t } = useTranslation("common");

  return (
    <SettingsCard>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("language.label")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("language.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <SettingsCardContent>
        <div className="max-w-xs">
          <I18nControls />
        </div>
      </SettingsCardContent>

      <SettingsCardFooter>{t("language.info")}</SettingsCardFooter>
    </SettingsCard>
  );
};
