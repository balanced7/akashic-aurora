"use client";

import { useMutation } from "@tanstack/react-query";
import { memo } from "react";

import { SocialProvider as SocialProviderType } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Badge } from "@akashic-labs/ui-web/badge";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { useAuthFormStore } from "~/modules/auth/form/store";

import { auth } from "../lib/api";

import type { AuthProvider } from "@akashic-labs/auth";
import type { Icon } from "@akashic-labs/ui-web/icons";

interface SocialProvidersProps {
  readonly providers: SocialProviderType[];
  readonly redirectTo?: string;
}

export const SocialIcons: Record<SocialProviderType, Icon> = {
  [SocialProviderType.GITHUB]: Icons.Github,
  [SocialProviderType.GOOGLE]: Icons.Google,
  [SocialProviderType.APPLE]: Icons.Apple,
};

const SocialProvider = ({
  provider,
  isSubmitting,
  onClick,
  actualProvider,
}: {
  provider: SocialProviderType;
  isSubmitting: boolean;
  onClick: () => void;
  actualProvider: AuthProvider;
}) => {
  const { t } = useTranslation("common");
  const Icon = SocialIcons[provider];

  return (
    <Button
      key={provider}
      variant="outline"
      type="button"
      size="lg"
      className="relative grow basis-28 gap-2"
      disabled={isSubmitting}
      onClick={onClick}
    >
      {isSubmitting && actualProvider === provider ? (
        <Icons.Loader2 className="animate-spin" />
      ) : (
        <>
          <Icon className="size-5 dark:brightness-125" />
          <span className="leading-none capitalize">{provider}</span>
        </>
      )}

      {authClient.isLastUsedLoginMethod(provider) && (
        <Badge className="absolute top-0 -right-4 z-10 -translate-y-1/2 shadow-sm">
          {t("lastUsed")}
        </Badge>
      )}
    </Button>
  );
};

export const SocialProviders = memo<SocialProvidersProps>(
  ({ providers, redirectTo = pathsConfig.dashboard.user.index }) => {
    const {
      provider: actualProvider,
      setProvider,
      isSubmitting,
      setIsSubmitting,
    } = useAuthFormStore();

    const signIn = useMutation({
      ...auth.mutations.signIn.social,
      onMutate: ({ provider }) => {
        setProvider(provider as SocialProviderType);
        setIsSubmitting(true);
      },
      onSettled: () => {
        setIsSubmitting(false);
      },
    });

    return (
      <div className="flex flex-wrap gap-2">
        {Object.values(providers).map((provider) => (
          <SocialProvider
            key={provider}
            provider={provider}
            isSubmitting={isSubmitting}
            onClick={() =>
              signIn.mutate({
                provider,
                callbackURL: redirectTo,
                errorCallbackURL: pathsConfig.auth.error,
              })
            }
            actualProvider={actualProvider}
          />
        ))}
      </div>
    );
  },
);

SocialProviders.displayName = "SocialProviders";
