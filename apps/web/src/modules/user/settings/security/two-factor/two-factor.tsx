"use client";

import { useCallback, useMemo, useState } from "react";

import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import { Switch } from "@akashic-labs/ui-web/switch";

import {
  SettingsCard,
  SettingsCardHeader,
  SettingsCardTitle,
  SettingsCardDescription,
  SettingsCardContent,
  SettingsCardFooter,
} from "~/modules/common/layout/dashboard/settings-card";

import { RequirePassword } from "../require-password";

import { BackupCodesTile } from "./backup-codes/backup-codes";
import { useBackupCodes } from "./backup-codes/use-backup-codes";
import { TotpModal, TotpTile } from "./totp/totp";
import { useTotp } from "./totp/use-totp";
import { useTwoFactor } from "./use-two-factor";

import type { PasswordPayload } from "@akashic-labs/auth";

export const TwoFactorAuthentication = () => {
  const { t } = useTranslation(["auth", "common"]);
  const [twoFactorOpen, setTwoFactorOpen] = useState(false);
  const [totpOpen, setTotpOpen] = useState(false);

  const { setUri } = useTotp();
  const { setCodes } = useBackupCodes();

  const { enabled, enable, disable } = useTwoFactor();

  const onEnable = useCallback(
    async (data: PasswordPayload) => {
      const response = await enable.mutateAsync(data);

      setUri(response.totpURI);
      setCodes(response.backupCodes);
      setTwoFactorOpen(false);
      setTotpOpen(true);
    },
    [enable, setUri, setCodes, setTwoFactorOpen, setTotpOpen],
  );

  const onDisable = useCallback(
    async (data: PasswordPayload) => {
      await disable.mutateAsync(data);
    },
    [disable],
  );

  return (
    <SettingsCard className="h-fit w-full overflow-hidden">
      <SettingsCardHeader className="flex flex-row items-start justify-between gap-2">
        <div className="space-y-1.5">
          <SettingsCardTitle>{t("account.twoFactor.title")}</SettingsCardTitle>
          <SettingsCardDescription>
            {t("account.twoFactor.description")}
          </SettingsCardDescription>
        </div>

        <TwoFactorSwitch
          onSubmit={enabled ? onDisable : onEnable}
          open={twoFactorOpen}
          onOpenChange={setTwoFactorOpen}
        />
        <TotpModal open={totpOpen} onOpenChange={setTotpOpen} />
      </SettingsCardHeader>

      <SettingsCardContent className="space-y-4">
        <TotpTile />
        <BackupCodesTile />
      </SettingsCardContent>
      <SettingsCardFooter>
        <span>{t("account.twoFactor.info")}</span>
      </SettingsCardFooter>
    </SettingsCard>
  );
};

const TwoFactorSwitch = ({
  open,
  onOpenChange,
  onSubmit,
}: {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSubmit: (data: PasswordPayload) => Promise<void>;
}) => {
  const { t } = useTranslation(["common", "auth"]);

  const { enabled } = useTwoFactor();

  const key = useMemo(() => {
    return enabled ? "disable" : "enable";
  }, [enabled]);

  return (
    <RequirePassword
      onConfirm={onSubmit}
      open={open}
      onOpenChange={onOpenChange}
      title={t(`account.twoFactor.${key}.title`)}
      description={t(`account.twoFactor.${key}.description`)}
      cta={t(key)}
    >
      <Switch
        checked={enabled}
        className={cn({
          "bg-input": !enabled,
          "bg-primary": enabled,
        })}
      />
    </RequirePassword>
  );
};
