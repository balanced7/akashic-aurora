"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { MemberRole } from "@akashic-labs/auth";
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
import { authClient } from "~/lib/auth/client";
import {
  SettingsCard,
  SettingsCardHeader,
  SettingsCardTitle,
  SettingsCardDescription,
  SettingsCardFooter,
} from "~/modules/common/layout/dashboard/settings-card";
import { organization } from "~/modules/organization/lib/api";

import { useActiveOrganization } from "../hooks/use-active-organization";

export const DeleteOrganization = ({
  organizationId,
}: {
  organizationId: string;
}) => {
  const { t } = useTranslation("organization");
  const { activeMember } = useActiveOrganization();

  const { data: activeOrganization } = useQuery(
    organization.queries.get({ id: organizationId }),
  );

  if (!activeOrganization) {
    return null;
  }

  const hasDeletePermission = authClient.organization.checkRolePermission({
    permission: {
      organization: ["delete"],
    },
    role: activeMember?.role ?? MemberRole.MEMBER,
  });

  return (
    <SettingsCard variant="destructive" disabled={!hasDeletePermission}>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("delete.title")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("delete.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <SettingsCardFooter>
        {hasDeletePermission ? (
          <ConfirmModal organizationId={activeOrganization.id}>
            <Button size="sm" className="ml-auto" variant="destructive">
              {t("delete.cta")}
            </Button>
          </ConfirmModal>
        ) : (
          t("delete.missingPermission")
        )}
      </SettingsCardFooter>
    </SettingsCard>
  );
};

const ConfirmModal = ({
  children,
  organizationId,
}: {
  children: React.ReactNode;
  organizationId: string;
}) => {
  const { t } = useTranslation(["common", "organization"]);
  const router = useRouter();

  const deleteOrganization = useMutation({
    ...organization.mutations.delete,
    onSuccess: () => {
      toast.success(t("delete.success"));
      router.replace(pathsConfig.dashboard.user.index);
    },
  });

  const handleDelete = () => {
    deleteOrganization.mutate({ organizationId });
  };

  return (
    <Modal>
      <ModalTrigger asChild>{children}</ModalTrigger>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>{t("delete.title")}</ModalTitle>
          <ModalDescription className="whitespace-pre-line">
            {t("delete.disclaimer")}
          </ModalDescription>
        </ModalHeader>
        <ModalFooter>
          <ModalClose asChild>
            <Button variant="outline">{t("cancel")}</Button>
          </ModalClose>
          <Button
            onClick={handleDelete}
            variant="destructive"
            disabled={deleteOrganization.isPending}
          >
            {deleteOrganization.isPending ? (
              <Icons.Loader2 className="animate-spin" />
            ) : (
              t("common:delete")
            )}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
