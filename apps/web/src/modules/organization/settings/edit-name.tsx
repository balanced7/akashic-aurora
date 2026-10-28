"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { MemberRole, updateOrganizationSchema } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Input } from "@akashic-labs/ui-web/input";

import { authClient } from "~/lib/auth/client";
import {
  SettingsCard,
  SettingsCardContent,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";
import { organization } from "~/modules/organization/lib/api";
import { onPromise } from "~/utils";

import { useActiveOrganization } from "../hooks/use-active-organization";

export const EditName = ({ organizationId }: { organizationId: string }) => {
  const { t } = useTranslation(["common", "organization"]);
  const { activeMember } = useActiveOrganization();

  const queryClient = useQueryClient();
  const { data: activeOrganization } = useQuery(
    organization.queries.get({ id: organizationId }),
  );

  const form = useForm({
    resolver: standardSchemaResolver(
      updateOrganizationSchema.pick({ name: true }),
    ),
    defaultValues: {
      name: activeOrganization?.name,
    },
  });

  const updateOrganization = useMutation({
    ...organization.mutations.update,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries(
          organization.queries.get({ id: organizationId }),
        ),
        ...(activeOrganization
          ? [
              queryClient.invalidateQueries(
                organization.queries.get({ slug: activeOrganization.slug }),
              ),
            ]
          : []),
      ]);
      toast.success(t("name.edit.success"));
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
      <SettingsCardHeader>
        <SettingsCardTitle>{t("common:name")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("name.edit.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <Form {...form}>
        <form
          onSubmit={onPromise(
            form.handleSubmit((data) =>
              updateOrganization.mutateAsync({ data, organizationId }),
            ),
          )}
        >
          <SettingsCardContent>
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Input
                      {...field}
                      type="text"
                      disabled={
                        !hasUpdatePermission || form.formState.isSubmitting
                      }
                      className="max-w-xs"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </SettingsCardContent>

          <SettingsCardFooter>
            {hasUpdatePermission ? (
              <>
                {t("name.edit.info")}
                <Button size="sm" disabled={form.formState.isSubmitting}>
                  {form.formState.isSubmitting ? (
                    <Icons.Loader2 className="size-4 animate-spin" />
                  ) : (
                    t("common:save")
                  )}
                </Button>
              </>
            ) : (
              t("name.edit.missingPermission")
            )}
          </SettingsCardFooter>
        </form>
      </Form>
    </SettingsCard>
  );
};
