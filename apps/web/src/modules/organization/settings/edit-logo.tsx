"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { MemberRole } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";

import { authClient } from "~/lib/auth/client";
import {
  AvatarForm,
  AvatarFormErrorMessage,
  AvatarFormInput,
  AvatarFormPreview,
  AvatarFormRemoveButton,
} from "~/modules/common/avatar-form";
import {
  SettingsCard,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";
import { organization } from "~/modules/organization/lib/api";

import { useActiveOrganization } from "../hooks/use-active-organization";

export const EditLogo = ({ organizationId }: { organizationId: string }) => {
  const { t } = useTranslation(["common", "validation", "organization"]);
  const { activeMember } = useActiveOrganization();

  const queryClient = useQueryClient();
  const { data: activeOrganization } = useQuery(
    organization.queries.get({ id: organizationId }),
  );

  const updateOrganization = useMutation({
    ...organization.mutations.update,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries(
          organization.queries.get({ id: organizationId }),
        ),
      ]);
    },
  });

  if (!activeOrganization) {
    return null;
  }

  const hasUpdatePermission = authClient.organization.checkRolePermission({
    permission: {
      organization: ["update"],
    },
    role: activeMember?.role ?? MemberRole.MEMBER,
  });

  return (
    <SettingsCard disabled={!hasUpdatePermission}>
      <SettingsCardHeader className="block">
        <AvatarForm
          id={activeOrganization.id}
          image={activeOrganization.logo}
          update={(image) =>
            updateOrganization.mutateAsync({
              data: { logo: image ?? "" },
              organizationId: activeOrganization.id,
            })
          }
        >
          <div className="relative float-right">
            <AvatarFormInput
              onUpload={async () => {
                toast.success(t("logo.update.success"));
                await Promise.all([
                  queryClient.invalidateQueries(
                    organization.queries.get({ id: activeOrganization.id }),
                  ),
                  queryClient.invalidateQueries(
                    organization.queries.get({ slug: activeOrganization.slug }),
                  ),
                ]);
              }}
              disabled={!hasUpdatePermission}
            >
              <AvatarFormPreview
                fallback={
                  <span className="text-muted-foreground text-3xl uppercase">
                    {activeOrganization.name.charAt(0)}
                  </span>
                }
              />
            </AvatarFormInput>

            {hasUpdatePermission && (
              <AvatarFormRemoveButton
                onRemove={async () => {
                  toast.success(t("logo.remove.success"));
                  await Promise.all([
                    queryClient.invalidateQueries(
                      organization.queries.get({ id: activeOrganization.id }),
                    ),
                    queryClient.invalidateQueries(
                      organization.queries.get({
                        slug: activeOrganization.slug,
                      }),
                    ),
                  ]);
                }}
              />
            )}
          </div>
          <SettingsCardTitle>{t("common:logo")}</SettingsCardTitle>
          <SettingsCardDescription className="py-1.5 whitespace-pre-line">
            {t("logo.description")}
          </SettingsCardDescription>

          <AvatarFormErrorMessage className="mt-1" />
        </AvatarForm>
      </SettingsCardHeader>

      <SettingsCardFooter>
        {hasUpdatePermission ? t("logo.info") : t("logo.missingPermission")}
      </SettingsCardFooter>
    </SettingsCard>
  );
};
