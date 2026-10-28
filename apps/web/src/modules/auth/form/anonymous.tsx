"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { AuthProvider } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";

import { auth } from "../lib/api";

import { useAuthFormStore } from "./store";

interface AnonymousLoginProps {
  readonly redirectTo?: string;
}

export const AnonymousLogin = ({
  redirectTo = pathsConfig.dashboard.user.index,
}: AnonymousLoginProps) => {
  const router = useRouter();
  const { t } = useTranslation("auth");
  const { provider, setProvider, isSubmitting, setIsSubmitting } =
    useAuthFormStore();

  const signIn = useMutation({
    ...auth.mutations.signIn.anonymous,
    onMutate: () => {
      setProvider(AuthProvider.ANONYMOUS);
      setIsSubmitting(true);
    },
    onSettled: () => {
      setIsSubmitting(false);
    },
    onSuccess: () => {
      router.replace(redirectTo);
    },
  });

  return (
    <Button
      variant="outline"
      className="gap-2"
      size="lg"
      type="button"
      disabled={isSubmitting}
      onClick={() => signIn.mutate(undefined)}
    >
      {isSubmitting && provider === AuthProvider.ANONYMOUS ? (
        <Icons.Loader2 className="animate-spin" />
      ) : (
        <>
          <Icons.UserRound className="size-4" />
          {t("login.anonymous.cta")}
        </>
      )}
    </Button>
  );
};
