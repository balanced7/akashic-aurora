"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
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
import { authClient } from "~/lib/auth/client";
import {
  SettingsCard,
  SettingsCardHeader,
  SettingsCardTitle,
  SettingsCardDescription,
  SettingsCardFooter,
} from "~/modules/common/layout/dashboard/settings-card";
import { organization } from "~/modules/organization/lib/api";

export const LeaveOrganization = ({
  organizationId,
}: {
  organizationId: string;
}) => {
  const { t } = useTranslation("organization");

  const { data: activeOrganization } = useQuery(
    organization.queries.get({ id: organizationId }),
  );

  const { data: isOnlyOwner } = useQuery({
    ...organization.queries.members.getIsOnlyOwner({ id: organizationId }),
    retry: false,
  });

  const canLeave = !isOnlyOwner?.status;

  if (!activeOrganization) {
    return null;
  }

  return (
    <SettingsCard variant="destructive" disabled={!canLeave}>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("leave.title")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("leave.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <SettingsCardFooter>
        {canLeave ? (
          <ConfirmLeaveModal organizationId={activeOrganization.id}>
            <Button size="sm" className="ml-auto" variant="destructive">
              {t("leave.cta")}
            </Button>
          </ConfirmLeaveModal>
        ) : (
          t("leave.cannotLeaveAsOnlyOwner")
        )}
      </SettingsCardFooter>
    </SettingsCard>
  );
};

const ConfirmLeaveModal = ({
  children,
  organizationId,
}: {
  children: React.ReactNode;
  organizationId: string;
}) => {
  const { t } = useTranslation(["common", "organization"]);
  const router = useRouter();
  const { refetch } = authClient.useListOrganizations();

  const leaveOrganization = useMutation({
    ...organization.mutations.leave,
    onSuccess: async () => {
      await refetch();
      toast.success(t("leave.success"));
      router.replace(pathsConfig.dashboard.user.index);
    },
  });

  const handleLeave = () => {
    leaveOrganization.mutate({ organizationId });
  };

  return (
    <Modal>
      <ModalTrigger asChild>{children}</ModalTrigger>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>{t("leave.title")}</ModalTitle>
          <ModalDescription className="whitespace-pre-line">
            {t("leave.disclaimer")}
          </ModalDescription>
        </ModalHeader>
        <ModalFooter>
          <ModalClose asChild>
            <Button variant="outline">{t("cancel")}</Button>
          </ModalClose>
          <Button
            onClick={handleLeave}
            variant="destructive"
            disabled={leaveOrganization.isPending}
          >
            {leaveOrganization.isPending ? (
              <Icons.Loader2 className="animate-spin" />
            ) : (
              t("common:leave")
            )}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
