"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AuthProvider } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Badge } from "@akashic-labs/ui-web/badge";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";

import { auth } from "../../lib/api";
import { useAuthFormStore } from "../store";

interface PasskeyLoginProps {
  readonly redirectTo?: string;
}

export const PasskeyLogin = ({
  redirectTo = pathsConfig.dashboard.user.index,
}: PasskeyLoginProps) => {
  const router = useRouter();
  const { setProvider, setIsSubmitting, isSubmitting, provider } =
    useAuthFormStore();
  const { t } = useTranslation(["auth", "common"]);

  const signIn = useMutation({
    ...auth.mutations.signIn.passkey,
    onMutate: () => {
      setProvider(AuthProvider.PASSKEY);
      setIsSubmitting(true);
    },
    onSettled: () => {
      setIsSubmitting(false);
    },
    onSuccess: () => {
      router.replace(redirectTo);
    },
  });

  useEffect(() => {
    void auth.mutations.signIn.passkey.mutationFn({ autoFill: true });
  }, []);

  return (
    <Button
      variant="outline"
      className="relative gap-2"
      size="lg"
      onClick={() => signIn.mutate(undefined)}
      disabled={isSubmitting}
    >
      {isSubmitting && provider === AuthProvider.PASSKEY ? (
        <Icons.Loader2 className="size-4 animate-spin" />
      ) : (
        <>
          <Icons.Key className="size-4" />
          {t("login.passkey.cta")}
        </>
      )}

      {authClient.isLastUsedLoginMethod(AuthProvider.PASSKEY) && (
        <Badge className="absolute top-0 -right-4 z-10 -translate-y-1/2 shadow-sm">
          {t("lastUsed")}
        </Badge>
      )}
    </Button>
  );
};
