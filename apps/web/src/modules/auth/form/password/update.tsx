"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { motion } from "motion/react";
import { useRouter } from "next/navigation";
import { memo } from "react";
import { useForm } from "react-hook-form";

import { updatePasswordSchema } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
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

import { pathsConfig } from "~/config/paths";
import { onPromise } from "~/utils";

import { auth } from "../../lib/api";

interface UpdatePasswordFormProps {
  readonly token?: string;
}

export const UpdatePasswordForm = memo<UpdatePasswordFormProps>(({ token }) => {
  const { t } = useTranslation("auth");
  const router = useRouter();
  const form = useForm({
    resolver: standardSchemaResolver(updatePasswordSchema),
  });

  const resetPassword = useMutation({
    ...auth.mutations.password.reset,
    onSuccess: () => {
      router.replace(pathsConfig.auth.login);
    },
  });

  return (
    <Form {...form} key="idle">
      <motion.form
        onSubmit={onPromise(
          form.handleSubmit((data) =>
            resetPassword.mutateAsync({
              newPassword: data.password,
              token,
            }),
          ),
        )}
        className="space-y-6"
        exit={{ opacity: 0 }}
      >
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("password")}</FormLabel>
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

        <Button
          type="submit"
          className="w-full"
          size="lg"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? (
            <Icons.Loader2 className="animate-spin" />
          ) : (
            t("account.password.update.cta")
          )}
        </Button>
      </motion.form>
    </Form>
  );
});

UpdatePasswordForm.displayName = "UpdatePasswordForm";
