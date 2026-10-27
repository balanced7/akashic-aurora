"use client";

import { useTranslation } from "@akashic-labs/i18n";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@akashic-labs/ui-web/alert";
import { Icons } from "@akashic-labs/ui-web/icons";

export const InvitationDisclaimer = () => {
  const { t } = useTranslation("organization");

  return (
    <Alert variant="primary">
      <Icons.MailPlus />
      <AlertTitle>{t("invitations.disclaimer.title")}</AlertTitle>
      <AlertDescription>
        {t("invitations.disclaimer.description")}
      </AlertDescription>
    </Alert>
  );
};
