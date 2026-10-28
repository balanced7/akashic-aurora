import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useTheme } from "next-themes";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import QRCode from "react-qr-code";

import { otpSchema } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import {
  FormField,
  FormControl,
  FormItem,
  FormMessage,
  Form,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@akashic-labs/ui-web/input-otp";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
  ModalClose,
} from "@akashic-labs/ui-web/modal";

import { useCopyToClipboard } from "~/modules/common/hooks/use-copy-to-clipboard";

import { RequirePassword } from "../../require-password";
import { BackupCodesModal } from "../backup-codes/backup-codes";
import { useTwoFactor } from "../use-two-factor";

import { useTotp } from "./use-totp";

import type { OtpPayload, PasswordPayload } from "@akashic-labs/auth";

interface TotpModalProps {
  readonly open?: boolean;
  readonly onOpenChange?: (open: boolean) => void;
}

export const TotpModal = ({ open, onOpenChange }: TotpModalProps) => {
  const { resolvedTheme } = useTheme();
  const [backupCodesOpen, setBackupCodesOpen] = useState(false);
  const { t } = useTranslation(["common", "auth"]);

  const { uri, verify } = useTotp();
  const form = useForm({
    resolver: standardSchemaResolver(otpSchema),
    defaultValues: {
      code: "",
    },
  });

  const onSubmit = async (data: OtpPayload) => {
    try {
      if (document.activeElement && "blur" in document.activeElement) {
        (document.activeElement as HTMLElement).blur();
      }
      await verify.mutateAsync(data);
      onOpenChange?.(false);
      setBackupCodesOpen(true);
    } catch (error) {
      setTimeout(() => form.setFocus("code"), 0);
      throw error;
    }
  };

  return (
    <>
      <Modal open={open} onOpenChange={onOpenChange}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>{t("account.twoFactor.totp.enable.title")}</ModalTitle>
            <ModalDescription className="whitespace-pre-line">
              {t("account.twoFactor.totp.enable.description")}
            </ModalDescription>
          </ModalHeader>

          <div className="mt-2 flex w-full flex-col-reverse items-center gap-2">
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="mt-2 flex w-full flex-col items-center space-y-4 md:space-y-6"
              >
                <FormField
                  control={form.control}
                  name="code"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <InputOTP
                          maxLength={6}
                          disabled={form.formState.isSubmitting}
                          onComplete={form.handleSubmit(onSubmit)}
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
                <ModalFooter className="flex w-full justify-end">
                  <ModalClose asChild>
                    <Button variant="outline" type="button">
                      {t("close")}
                    </Button>
                  </ModalClose>
                  <Button type="submit" disabled={form.formState.isSubmitting}>
                    {form.formState.isSubmitting ? (
                      <Icons.Loader2 className="size-4 animate-spin" />
                    ) : (
                      t("continue")
                    )}
                  </Button>
                </ModalFooter>
              </form>
            </Form>

            <QRCode
              value={uri}
              size={180}
              bgColor="transparent"
              fgColor={resolvedTheme === "dark" ? "#fff" : "#000"}
            />

            <Secret />
          </div>
        </ModalContent>
      </Modal>
      <BackupCodesModal
        open={backupCodesOpen}
        onOpenChange={setBackupCodesOpen}
      />
    </>
  );
};

const Secret = () => {
  const { uri } = useTotp();
  const [showCheck, setShowCheck] = useState(false);

  const [, copy] = useCopyToClipboard();

  const secret = useMemo(() => {
    return uri ? new URL(uri).searchParams.get("secret") : null;
  }, [uri]);

  const handleCopy = async () => {
    const success = await copy(secret ?? "");
    if (!success) {
      return;
    }

    setShowCheck(true);
    setTimeout(() => {
      setShowCheck(false);
    }, 2000);
  };

  if (!secret) {
    return null;
  }

  return (
    <span className="mb-1 inline-block w-full gap-2 px-6 text-center leading-none text-balance">
      <span className="font-mono text-sm leading-none text-balance break-all">
        {secret}
      </span>
      <Button
        variant="ghost"
        size="icon"
        className="ml-1 size-6"
        type="button"
        onClick={handleCopy}
      >
        {showCheck ? (
          <Icons.Check className="size-3" />
        ) : (
          <Icons.Copy className="size-3" />
        )}
      </Button>
    </span>
  );
};

export const TotpTile = () => {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation(["common", "auth"]);
  const { enabled } = useTwoFactor();

  const { setUri, getUri } = useTotp();

  const onEdit = async (data: PasswordPayload) => {
    const response = await getUri.mutateAsync(data);
    setUri(response.totpURI);
    setOpen(true);
  };

  return (
    <div className="flex items-center justify-between gap-4 rounded-md border p-4">
      <div>
        <span className="text-sm font-medium">
          {t("account.twoFactor.totp.title")}
        </span>
        <p className="text-muted-foreground text-sm">
          {t("account.twoFactor.totp.description")}
        </p>
      </div>

      <RequirePassword onConfirm={onEdit}>
        <Button variant="outline" disabled={!enabled}>
          {enabled ? t("edit") : t("add")}
        </Button>
      </RequirePassword>
      <TotpModal open={open} onOpenChange={setOpen} />
    </div>
  );
};
