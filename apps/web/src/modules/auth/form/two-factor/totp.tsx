"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { memo } from "react";
import { useForm } from "react-hook-form";

import { otpVerificationSchema, SecondFactor } from "@akashic-labs/auth";
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
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@akashic-labs/ui-web/input-otp";

import { pathsConfig } from "~/config/paths";

import { auth } from "../../lib/api";

import type { CtaProps, FormProps } from ".";

const TotpForm = memo<FormProps>(
  ({ redirectTo = pathsConfig.dashboard.user.index }) => {
    const router = useRouter();
    const { t } = useTranslation(["common", "auth"]);

    const form = useForm({
      resolver: standardSchemaResolver(otpVerificationSchema),
      defaultValues: {
        code: "",
        trustDevice: false,
      },
    });

    const verifyTotp = useMutation({
      ...auth.mutations.twoFactor.totp.verify,
      onSuccess: () => {
        router.replace(redirectTo);
      },
    });

    return (
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((data) => verifyTotp.mutateAsync(data))}
          className="flex flex-col gap-6"
        >
          <FormField
            control={form.control}
            name="code"
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <InputOTP
                    maxLength={6}
                    autoFocus
                    disabled={form.formState.isSubmitting}
                    onComplete={form.handleSubmit((data) =>
                      verifyTotp.mutateAsync(data),
                    )}
                    {...field}
                  >
                    <InputOTPGroup>
                      {Array.from({ length: 6 }).map((_, index) => (
                        <InputOTPSlot key={index} index={index} />
                      ))}
                    </InputOTPGroup>
                  </InputOTP>
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

const TotpCta = memo<CtaProps>(({ onFactorChange }) => {
  const { t } = useTranslation(["auth"]);
  return (
    <div className="flex items-center justify-center pt-2">
      <span
        role="link"
        onClick={() => onFactorChange(SecondFactor.TOTP)}
        className="text-muted-foreground hover:text-primary cursor-pointer pl-2 text-sm font-medium underline underline-offset-4"
      >
        {t("login.twoFactor.totp.cta")}
      </span>
    </div>
  );
});

export { TotpForm, TotpCta };
