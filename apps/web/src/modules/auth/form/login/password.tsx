"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { memo } from "react";
import { useForm } from "react-hook-form";

import { AuthProvider, passwordLoginSchema } from "@akashic-labs/auth";
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
import { Input, PasswordInput } from "@akashic-labs/ui-web/input";

import { pathsConfig } from "~/config/paths";
import { useAuthFormStore } from "~/modules/auth/form/store";
import { TurboLink } from "~/modules/common/turbo-link";
import { onPromise } from "~/utils";

import { auth } from "../../lib/api";

interface PasswordLoginFormProps {
  readonly redirectTo?: string;
  readonly email?: string;
  readonly onTwoFactorRedirect?: () => void;
}

export const PasswordLoginForm = memo<PasswordLoginFormProps>(
  ({
    redirectTo = pathsConfig.dashboard.user.index,
    email,
    onTwoFactorRedirect,
  }) => {
    const { t } = useTranslation(["common", "auth"]);
    const { provider, setProvider, isSubmitting, setIsSubmitting } =
      useAuthFormStore();

    const form = useForm({
      resolver: standardSchemaResolver(passwordLoginSchema),
      defaultValues: {
        rememberMe: true,
        email,
      },
    });

    const signIn = useMutation({
      ...auth.mutations.signIn.email,
      onMutate: () => {
        setProvider(AuthProvider.PASSWORD);
        setIsSubmitting(true);
      },
      onSettled: () => {
        setIsSubmitting(false);
      },
      onSuccess: (ctx) => {
        if ("twoFactorRedirect" in ctx) {
          return onTwoFactorRedirect?.();
        }
      },
    });

    return (
      <Form {...form}>
        <form
          onSubmit={onPromise(
            form.handleSubmit((data) =>
              signIn.mutateAsync({
                ...data,
                callbackURL: redirectTo,
              }),
            ),
          )}
          className="flex flex-col gap-6"
        >
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("common:email")}</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="email"
                    disabled={isSubmitting}
                    autoComplete="email webauthn"
                    inputMode="email"
                    spellCheck={false}
                    maxLength={254}
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
                <div className="flex flex-col-reverse gap-2">
                  <FormControl>
                    <PasswordInput
                      {...field}
                      disabled={isSubmitting}
                      autoComplete="current-password webauthn"
                    />
                  </FormControl>
                  <div className="flex w-full items-center justify-between">
                    <FormLabel>{t("password")}</FormLabel>
                    <TurboLink
                      href={pathsConfig.auth.forgotPassword}
                      className="text-muted-foreground hover:text-primary text-sm underline underline-offset-4"
                    >
                      {t("account.password.forgot.label")}
                    </TurboLink>
                  </div>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="rememberMe"
            render={({ field }) => (
              <FormItem className="-mt-2 ml-px flex items-center gap-2 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    disabled={isSubmitting}
                  />
                </FormControl>
                <FormLabel>{t("rememberMe")}</FormLabel>
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
              t("login.cta")
            )}
          </Button>
        </form>
      </Form>
    );
  },
);

PasswordLoginForm.displayName = "PasswordLoginForm";
