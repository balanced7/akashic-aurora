"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { useTranslation } from "@akashic-labs/i18n";
import { capitalize } from "@akashic-labs/shared/utils";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";
import {
  Modal,
  ModalTrigger,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
  ModalClose,
} from "@akashic-labs/ui-web/modal";
import { Skeleton } from "@akashic-labs/ui-web/skeleton";

import { authConfig } from "~/config/auth";
import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";
import { SocialIcons } from "~/modules/auth/form/social-providers";
import { auth } from "~/modules/auth/lib/api";
import {
  SettingsCard,
  SettingsCardContent,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";

import type { SocialProvider } from "@akashic-labs/auth";

export const Accounts = () => {
  const { t, i18n } = useTranslation(["auth", "common"]);
  const { data: session } = authClient.useSession();

  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    ...auth.queries.accounts.getAll,
    enabled: !!session?.user.id,
  });

  const accounts = data ?? [];
  const socials = accounts.filter((account) =>
    authConfig.providers.oAuth.includes(account.providerId),
  );
  const missing = authConfig.providers.oAuth.filter(
    (provider) => !socials.some((social) => social.providerId === provider),
  );

  const connect = useMutation({
    ...auth.mutations.accounts.connect,
    onSuccess: async (_, { provider }) => {
      await queryClient.invalidateQueries(auth.queries.accounts.getAll);
      toast.success(
        t("account.accounts.connect.success", {
          provider: capitalize(provider as string),
        }),
      );
    },
  });

  const disconnect = useMutation({
    ...auth.mutations.accounts.disconnect,
    onSuccess: async (_, { providerId }) => {
      await queryClient.invalidateQueries(auth.queries.accounts.getAll);
      toast.success(
        t("account.accounts.disconnect.success", {
          provider: capitalize(providerId),
        }),
      );
    },
  });

  return (
    <SettingsCard>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("account.accounts.title")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("account.accounts.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <SettingsCardContent className="space-y-4">
        {isLoading && <Skeleton className="h-24" />}

        {socials.length > 0 && !isLoading && (
          <ul className="overflow-hidden rounded-md border">
            {socials.map((social) => {
              const provider = social.providerId as SocialProvider;
              const Icon = SocialIcons[provider];

              return (
                <li
                  key={social.accountId}
                  className="flex items-center gap-3 border-b px-4 py-3 last:border-b-0"
                >
                  <Icon className="size-8" />

                  <div className="mr-auto flex flex-col">
                    <span className="text-sm font-medium capitalize">
                      {provider}
                    </span>
                    <span className="text-muted-foreground text-xs">
                      {t("account.accounts.connectedAt", {
                        date: social.updatedAt.toLocaleDateString(
                          i18n.language,
                        ),
                      })}
                    </span>
                  </div>

                  <ConfirmModal
                    provider={provider}
                    onConfirm={() =>
                      disconnect.mutate({ providerId: provider })
                    }
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      disabled={accounts.length === 1 || disconnect.isPending}
                    >
                      <span className="sr-only">
                        {t("account.accounts.disconnect.cta", {
                          provider,
                        })}
                      </span>
                      {disconnect.isPending &&
                      disconnect.variables.providerId === provider ? (
                        <Icons.Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Icons.Trash className="size-4" />
                      )}
                    </Button>
                  </ConfirmModal>
                </li>
              );
            })}
          </ul>
        )}

        {missing.length > 0 && !isLoading && (
          <div className="flex flex-col items-start gap-3 rounded-md border border-dashed px-4 py-3">
            <div className="flex items-center justify-center gap-1">
              <Icons.Plus className="size-4" />
              <span className="text-sm font-medium">{t("addNew")}</span>
            </div>

            <hr className="bg-border w-full" />
            <div className="flex flex-wrap gap-2">
              {missing.map((provider) => {
                const Icon = SocialIcons[provider];

                return (
                  <Button
                    variant="outline"
                    className="gap-2 px-3 capitalize"
                    key={provider}
                    disabled={connect.isPending}
                    onClick={() =>
                      connect.mutate({
                        provider,
                        callbackURL:
                          pathsConfig.dashboard.user.settings.security,
                        errorCallbackURL: pathsConfig.auth.error,
                      })
                    }
                  >
                    {connect.isPending &&
                    connect.variables.provider === provider ? (
                      <Icons.Loader2 className="size-6 animate-spin" />
                    ) : (
                      <Icon className="size-6" />
                    )}
                    {provider}
                  </Button>
                );
              })}
            </div>
          </div>
        )}
      </SettingsCardContent>

      <SettingsCardFooter>
        <span>{t("account.accounts.info")}</span>
      </SettingsCardFooter>
    </SettingsCard>
  );
};

const ConfirmModal = ({
  provider,
  children,
  onConfirm,
}: {
  provider: SocialProvider;
  children: React.ReactNode;
  onConfirm: () => void;
}) => {
  const { t } = useTranslation(["common", "auth"]);

  return (
    <Modal>
      <ModalTrigger asChild>{children}</ModalTrigger>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>
            {t("account.accounts.disconnect.cta", {
              provider: capitalize(provider),
            })}
          </ModalTitle>
          <ModalDescription className="whitespace-pre-line">
            {t("account.accounts.disconnect.disclaimer", {
              provider: capitalize(provider),
            })}
          </ModalDescription>
        </ModalHeader>
        <ModalFooter>
          <ModalClose asChild>
            <Button variant="outline">{t("cancel")}</Button>
          </ModalClose>
          <ModalClose asChild>
            <Button onClick={onConfirm}>{t("continue")}</Button>
          </ModalClose>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
