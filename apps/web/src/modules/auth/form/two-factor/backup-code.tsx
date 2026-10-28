"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { memo } from "react";
import { useForm } from "react-hook-form";

import { backupCodeVerificationSchema, SecondFactor } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Checkbox } from "@akashic-labs/ui-web/checkbox";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Input } from "@akashic-labs/ui-web/input";

import { pathsConfig } from "~/config/paths";

import { auth } from "../../lib/api";

import type { CtaProps, FormProps } from ".";

const BackupCodeForm = memo<FormProps>(
  ({ redirectTo = pathsConfig.dashboard.user.index }) => {
    const router = useRouter();
    const { t } = useTranslation(["common", "auth"]);
    const form = useForm({
      resolver: standardSchemaResolver(backupCodeVerificationSchema),
      defaultValues: {
        code: "",
        trustDevice: false,
      },
    });

    const verifyBackupCode = useMutation({
      ...auth.mutations.twoFactor.backupCodes.verify,
      onSuccess: () => {
        router.replace(redirectTo);
      },
    });

    return (
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((data) =>
            verifyBackupCode.mutateAsync(data),
          )}
          className="flex flex-col gap-6"
        >
          <FormField
            control={form.control}
            name="code"
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Input
                    {...field}
                    type="text"
                    autoFocus
                    disabled={form.formState.isSubmitting}
                    autoComplete="one-time-code"
                    placeholder={t("login.twoFactor.backupCode.placeholder")}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="trustDevice"
            render={({ field }) => (
              <FormItem className="-mt-2 ml-px flex items-center gap-2 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    disabled={form.formState.isSubmitting}
                  />
                </FormControl>
                <FormLabel>{t("login.twoFactor.trustDevice")}</FormLabel>
              </FormItem>
            )}
          />

          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting ? (
              <Icons.Loader2 className="animate-spin" />
            ) : (
              t("verify")
            )}
          </Button>
        </form>
      </Form>
    );
  },
);

const BackupCodeCta = memo<CtaProps>(({ onFactorChange }) => {
  const { t } = useTranslation(["auth"]);
  return (
    <div className="flex items-center justify-center pt-2">
      <span
        role="link"
        onClick={() => onFactorChange(SecondFactor.BACKUP_CODE)}
        className="text-muted-foreground hover:text-primary cursor-pointer pl-2 text-sm font-medium underline underline-offset-4"
      >
        {t("login.twoFactor.backupCode.cta")}
      </span>
    </div>
  );
});

export { BackupCodeForm, BackupCodeCta };
