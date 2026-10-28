"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useSearchParams } from "next/navigation";
import { memo } from "react";
import { useForm } from "react-hook-form";

import { AuthProvider, registerSchema, generateName } from "@akashic-labs/auth";
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
import { Input, PasswordInput } from "@akashic-labs/ui-web/input";

import { pathsConfig } from "~/config/paths";
import { TurboLink } from "~/modules/common/turbo-link";
import { onPromise } from "~/utils";

import { auth } from "../lib/api";

import { useAuthFormStore } from "./store";

interface RegisterFormProps {
  readonly redirectTo?: string;
  readonly email?: string;
}

export const RegisterForm = memo<RegisterFormProps>(
  ({ redirectTo = pathsConfig.dashboard.user.index, email }) => {
    const { t } = useTranslation(["common", "auth"]);
    const { provider, setProvider, isSubmitting, setIsSubmitting } =
      useAuthFormStore();

    const form = useForm({
      resolver: standardSchemaResolver(registerSchema),
      defaultValues: {
        email,
      },
    });

    const signUp = useMutation({
      ...auth.mutations.signUp.email,
      onMutate: () => {
        setProvider(AuthProvider.PASSWORD);
        setIsSubmitting(true);
      },
      onSettled: () => {
        setIsSubmitting(false);
      },
    });

    return (
      <AnimatePresence mode="wait">
        {form.formState.isSubmitSuccessful ? (
          <motion.div
            className="my-6 flex flex-col items-center justify-center gap-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            key="success"
          >
            <Icons.CheckCircle2
              className="text-success h-20 w-20"
              strokeWidth={1.2}
            />
            <h2 className="text-center text-2xl font-semibold tracking-tight">
              {t("register.success.title")}
            </h2>
            <p className="text-center">{t("register.success.description")}</p>
          </motion.div>
        ) : (
          <Form {...form} key="idle">
            <motion.form
              onSubmit={onPromise(
                form.handleSubmit((data) =>
                  signUp.mutateAsync({
                    ...data,
                    name: generateName(data.email),
                    callbackURL: redirectTo,
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
                        disabled={isSubmitting}
                        autoComplete="email"
                        inputMode="email"
                        spellCheck={false}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("password")}</FormLabel>
                    <FormControl>
                      <PasswordInput
                        {...field}
                        disabled={isSubmitting}
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
                disabled={isSubmitting}
              >
                {isSubmitting && provider === AuthProvider.PASSWORD ? (
                  <Icons.Loader2 className="animate-spin" />
                ) : (
                  t("register.cta")
                )}
              </Button>
            </motion.form>
          </Form>
        )}
      </AnimatePresence>
    );
  },
);

RegisterForm.displayName = "RegisterForm";

export const RegisterCta = () => {
  const { t } = useTranslation("auth");
  const searchParams = useSearchParams();

  return (
    <div className="flex items-center justify-center pt-2">
      <div className="text-muted-foreground text-sm">
        {t("login.noAccount")}
        <TurboLink
          href={
            searchParams.size > 0
              ? `${pathsConfig.auth.register}?${searchParams.toString()}`
              : pathsConfig.auth.register
          }
          className="hover:text-primary pl-2 font-medium underline underline-offset-4"
        >
          {t("register.cta")}!
        </TurboLink>
      </div>
    </div>
  );
};
