"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { memo, useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { passwordSchema } from "@akashic-labs/auth";
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
import {
  Modal,
  ModalClose,
  ModalContent,
  ModalDescription,
  ModalFooter,
  ModalHeader,
  ModalTitle,
  ModalTrigger,
} from "@akashic-labs/ui-web/modal";

import { onPromise } from "~/utils";

import type { PasswordPayload } from "@akashic-labs/auth";
import type { ComponentProps } from "react";
import type { UseFormReturn } from "react-hook-form";

interface PasswordFormProps {
  readonly form: UseFormReturn<PasswordPayload>;
  readonly onSubmit: (data: PasswordPayload) => Promise<void>;
  readonly children: React.ReactNode;
}

const PasswordForm = memo<PasswordFormProps>(({ form, onSubmit, children }) => {
  const { t } = useTranslation(["common", "auth"]);

  return (
    <Form {...form}>
      <form
        onSubmit={onPromise(form.handleSubmit(onSubmit))}
        className="space-y-4"
      >
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem className="w-full space-y-1 px-6 md:px-0">
              <FormLabel>{t("password")}</FormLabel>
              <FormControl>
                <PasswordInput
                  {...field}
                  autoComplete="current-password"
                  disabled={form.formState.isSubmitting}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {children}
      </form>
    </Form>
  );
});

PasswordForm.displayName = "PasswordForm";

interface RequirePasswordProps extends ComponentProps<typeof Modal> {
  readonly title?: string;
  readonly description?: string;
  readonly cta?: string;
  readonly onConfirm: (data: PasswordPayload) => Promise<void>;
}

export const RequirePassword = memo<RequirePasswordProps>(
  ({
    title,
    description,
    onConfirm,
    cta,
    children,
    open: _open,

    onOpenChange: _onOpenChange,
    ...props
  }) => {
    const [open, setOpen] = useState(_open ?? false);
    const { t } = useTranslation(["common", "auth"]);

    const form = useForm({
      resolver: standardSchemaResolver(passwordSchema),
      defaultValues: {
        password: "",
      },
    });

    const onSubmit = async (data: PasswordPayload) => {
      try {
        if (document.activeElement && "blur" in document.activeElement) {
          (document.activeElement as HTMLElement).blur();
        }
        await onConfirm(data);
        form.reset();
        setOpen(false);
      } catch (error) {
        setTimeout(() => form.setFocus("password"), 0);
        throw error;
      }
    };

    const onOpenChange = useCallback(
      (open: boolean) => {
        setOpen(open);
        _onOpenChange?.(open);
      },
      [_onOpenChange, setOpen],
    );

    useEffect(() => {
      setOpen(_open ?? false);
    }, [_open]);

    return (
      <Modal {...props} open={open} onOpenChange={onOpenChange}>
        <ModalTrigger asChild>{children}</ModalTrigger>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>
              {title ?? t("account.password.require.title")}
            </ModalTitle>
            <ModalDescription className="whitespace-pre-line">
              {description ?? t("account.password.require.description")}
            </ModalDescription>
          </ModalHeader>
          <PasswordForm form={form} onSubmit={onSubmit}>
            <ModalFooter>
              <ModalClose asChild>
                <Button variant="outline" type="button">
                  {t("cancel")}
                </Button>
              </ModalClose>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? (
                  <Icons.Loader2 className="size-4 animate-spin" />
                ) : (
                  (cta ?? t("continue"))
                )}
              </Button>
            </ModalFooter>
          </PasswordForm>
        </ModalContent>
      </Modal>
    );
  },
);

RequirePassword.displayName = "RequirePassword";
