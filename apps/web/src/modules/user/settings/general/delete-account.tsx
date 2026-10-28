"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";
import {
  Modal,
  ModalClose,
  ModalContent,
  ModalDescription,
  ModalFooter,
  ModalHeader,
  ModalTitle,
  ModalTrigger,
} from "@akashic-labs/ui-web/modal";

import { pathsConfig } from "~/config/paths";
import {
  SettingsCard,
  SettingsCardHeader,
  SettingsCardTitle,
  SettingsCardDescription,
  SettingsCardFooter,
} from "~/modules/common/layout/dashboard/settings-card";

import { user } from "../../lib/api";

export const DeleteAccount = () => {
  const { t } = useTranslation("auth");

  return (
    <SettingsCard variant="destructive">
      <SettingsCardHeader>
        <SettingsCardTitle>{t("account.delete.title")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("account.delete.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <SettingsCardFooter>
        <ConfirmModal>
          <Button size="sm" className="ml-auto" variant="destructive">
            {t("account.delete.cta")}
          </Button>
        </ConfirmModal>
      </SettingsCardFooter>
    </SettingsCard>
  );
};

const ConfirmModal = ({ children }: { children: React.ReactNode }) => {
  const { t } = useTranslation(["common", "auth"]);

  const deleteAccount = useMutation({
    ...user.mutations.delete,
    onSuccess: () => {
      toast.success(t("account.delete.confirmation.success"));
    },
  });

  return (
    <Modal>
      <ModalTrigger asChild>{children}</ModalTrigger>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>{t("account.delete.title")}</ModalTitle>
          <ModalDescription className="whitespace-pre-line">
            {t("account.delete.disclaimer")}
          </ModalDescription>
        </ModalHeader>
        <ModalFooter>
          <ModalClose asChild>
            <Button variant="outline">{t("cancel")}</Button>
          </ModalClose>
          <Button
            onClick={() =>
              deleteAccount.mutate({
                callbackURL: pathsConfig.index,
              })
            }
            variant="destructive"
            disabled={deleteAccount.isPending}
          >
            {deleteAccount.isPending ? (
              <Icons.Loader2 className="animate-spin" />
            ) : (
              t("account.delete.confirmation.cta")
            )}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
