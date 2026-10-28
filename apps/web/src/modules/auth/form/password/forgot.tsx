"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useForm } from "react-hook-form";

import { forgotPasswordSchema } from "@akashic-labs/auth";
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
import { Input } from "@akashic-labs/ui-web/input";

import { pathsConfig } from "~/config/paths";
import { TurboLink } from "~/modules/common/turbo-link";
import { onPromise } from "~/utils";

import { auth } from "../../lib/api";

export const ForgotPasswordForm = () => {
  const { t } = useTranslation(["common", "auth"]);
  const form = useForm({
    resolver: standardSchemaResolver(forgotPasswordSchema),
  });

  const forgetPassword = useMutation({
    ...auth.mutations.password.forget,
    onSuccess: () => {
      form.reset();
    },
  });

  return (
    <AnimatePresence mode="wait">
      {form.formState.isSubmitSuccessful ? (
        <motion.div
          className="mt-6 flex flex-col items-center justify-center gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          key="success"
        >
          <Icons.CheckCircle2
            className="text-success h-20 w-20"
            strokeWidth={1.2}
          />
          <h2 className="text-center text-2xl font-semibold tracking-tight">
            {t("account.password.forgot.success.title")}
          </h2>
          <p className="text-center">
            {t("account.password.forgot.success.description")}
          </p>
          <TurboLink
            href={pathsConfig.auth.login}
            className="text-muted-foreground hover:text-primary -mt-1 text-sm font-medium underline underline-offset-4"
          >
            {t("login.cta")}
          </TurboLink>
        </motion.div>
      ) : (
        <Form {...form} key="idle">
          <motion.form
            onSubmit={onPromise(
              form.handleSubmit((data) =>
                forgetPassword.mutateAsync({
                  ...data,
                  redirectTo: pathsConfig.auth.updatePassword,
                }),
              ),
            )}
            className="space-y-6"
            exit={{ opacity: 0 }}
          >
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("email")}</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      type="email"
                      disabled={form.formState.isSubmitting}
                      autoComplete="email"
                      inputMode="email"
                      spellCheck={false}
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
                t("account.password.forgot.cta")
              )}
            </Button>

            <div className="flex items-center justify-center pt-2">
              <TurboLink
                href={pathsConfig.auth.login}
                className="text-muted-foreground hover:text-primary pl-2 text-sm font-medium underline underline-offset-4"
              >
                {t("account.password.forgot.back")}
              </TurboLink>
            </div>
          </motion.form>
        </Form>
      )}
    </AnimatePresence>
  );
};
