"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { changePasswordSchema } from "@akashic-labs/auth";
import { Trans, useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { PasswordInput } from "@akashic-labs/ui-web/input";
import { Skeleton } from "@akashic-labs/ui-web/skeleton";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { auth } from "~/modules/auth/lib/api";
import {
  SettingsCard,
  SettingsCardContent,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";
import { TurboLink } from "~/modules/common/turbo-link";
import { onPromise } from "~/utils";

export const EditPassword = () => {
  const { t } = useTranslation(["common", "auth"]);
  const session = authClient.useSession();
  const { data: accounts, isLoading } = useQuery({
    ...auth.queries.accounts.getAll,
    enabled: !!session.data?.user.id,
  });

  const form = useForm({
    resolver: standardSchemaResolver(changePasswordSchema),
  });

  const changePassword = useMutation({
    ...auth.mutations.password.change,
    onSuccess: () => {
      toast.success(t("account.password.update.success"));
      form.reset();
    },
  });

  const hasPassword = accounts
    ?.map((account) => account.providerId)
    .includes("credential");

  return (
    <SettingsCard>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("password")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("account.password.update.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <Form {...form}>
        <form
          onSubmit={onPromise(
            form.handleSubmit((data) =>
              changePassword.mutateAsync({
                ...data,
                currentPassword: data.password,
                revokeOtherSessions: true,
              }),
            ),
          )}
        >
          <SettingsCardContent>
            {isLoading && <Skeleton className="mt-0 h-20" />}

            {!isLoading &&
              (hasPassword ? (
                <div className="flex w-full flex-wrap gap-3 lg:gap-5">
                  <FormField
                    control={form.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem className="w-full max-w-xs space-y-1">
                        <FormLabel>{t("currentPassword")}</FormLabel>
                        <FormControl>
                          <PasswordInput
                            {...field}
                            disabled={form.formState.isSubmitting}
                            autoComplete="current-password"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="newPassword"
                    render={({ field }) => (
                      <FormItem className="w-full max-w-xs space-y-1">
                        <FormLabel>{t("newPassword")}</FormLabel>
                        <FormControl>
                          <PasswordInput
                            {...field}
                            disabled={form.formState.isSubmitting}
                            autoComplete="new-password"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              ) : (
                <div className="flex w-full items-center justify-center rounded-md border border-dashed p-6">
                  <p className="text-center text-sm">
                    <Trans
                      i18nKey="account.password.update.noPassword"
                      ns="auth"
                      components={{
                        bold: (
                          <TurboLink
                            href={pathsConfig.auth.forgotPassword}
                            className="hover:text-primary font-medium underline underline-offset-4"
                          />
                        ),
                      }}
                    />
                  </p>
                </div>
              ))}
          </SettingsCardContent>
          <SettingsCardFooter>
            {t("account.password.update.info")}

            {!isLoading && hasPassword && (
              <Button size="sm" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? (
                  <Icons.Loader2 className="size-4 animate-spin" />
                ) : (
                  t("save")
                )}
              </Button>
            )}
          </SettingsCardFooter>
        </form>
      </Form>
    </SettingsCard>
  );
};
