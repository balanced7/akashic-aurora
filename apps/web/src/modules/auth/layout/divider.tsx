"use client";

import { useTranslation } from "@akashic-labs/i18n";

export const AuthDivider = () => {
  const { t } = useTranslation("auth");

  return (
    <div className="relative">
      <div className="absolute inset-0 flex items-center" aria-hidden="true">
        <div className="border-input w-full border-t" />
      </div>
      <div className="relative flex justify-center text-sm">
        <span className="bg-background text-muted-foreground px-2 leading-tight">
          {t("divider")}
        </span>
      </div>
    </div>
  );
};
