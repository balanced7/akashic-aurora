"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { memo } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { emailSchema } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import { Badge } from "@akashic-labs/ui-web/badge";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Form,
  FormMessage,
  FormField,
  FormControl,
  FormItem,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Input } from "@akashic-labs/ui-web/input";

import { pathsConfig } from "~/config/paths";
import { auth } from "~/modules/auth/lib/api";
import {
  SettingsCard,
  SettingsCardTitle,
  SettingsCardHeader,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardContent,
} from "~/modules/common/layout/dashboard/settings-card";

import type { User } from "@akashic-labs/auth";

interface EditEmailProps {
  readonly user: User;
}

export const EditEmail = memo<EditEmailProps>((props) => {
  const { t } = useTranslation(["common", "auth"]);
  const form = useForm({
    resolver: standardSchemaResolver(emailSchema),
    defaultValues: {
      email: props.user.email,
    },
  });

  const sendVerification = useMutation({
    ...auth.mutations.email.sendVerification,
    onSuccess: () => {
      toast.success(t("account.email.confirm.email.sent"));
    },
  });

  const changeEmail = useMutation({
    ...auth.mutations.email.change,
    onSuccess: () => {
      toast.success(t("account.email.change.success"));
    },
  });

  return (
    <SettingsCard>
      <SettingsCardHeader>
        <div className="flex items-center gap-3">
          <SettingsCardTitle>{t("email")}</SettingsCardTitle>
          <Badge
            className={cn({
              "bg-success/15 text-success hover:bg-success/25":
                props.user.emailVerified,
              "bg-destructive/15 text-destructive hover:bg-destructive/25":
                !props.user.emailVerified,
            })}
          >
            {props.user.emailVerified ? t("verified") : t("unverified")}
          </Badge>
          {!props.user.emailVerified && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                sendVerification.mutate({
                  email: props.user.email,
                  callbackURL: pathsConfig.dashboard.user.settings.index,
                })
              }
              disabled={sendVerification.isPending}
              type="button"
              className="h-auto px-3 py-1 text-xs"
            >
              {sendVerification.isPending
                ? t("account.email.confirm.loading")
                : t("account.email.confirm.cta")}
            </Button>
          )}
        </div>

        <SettingsCardDescription>
          {t("account.email.change.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((data) =>
            changeEmail.mutateAsync({
              newEmail: data.email,
              callbackURL: pathsConfig.dashboard.user.settings.index,
            }),
          )}
        >
          <SettingsCardContent>
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Input
                      {...field}
                      type="email"
                      className="max-w-xs"
                      placeholder="john@doe.com"
                      disabled={form.formState.isSubmitting}
                      autoComplete="email"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </SettingsCardContent>

          <SettingsCardFooter>
            {t("account.email.change.info")}
            <Button size="sm" disabled={form.formState.isSubmitting}>
              {form.formState.isSubmitting ? (
                <Icons.Loader2 className="size-4 animate-spin" />
              ) : (
                t("save")
              )}
            </Button>
          </SettingsCardFooter>
        </form>
      </Form>
    </SettingsCard>
  );
});

EditEmail.displayName = "EditEmail";
