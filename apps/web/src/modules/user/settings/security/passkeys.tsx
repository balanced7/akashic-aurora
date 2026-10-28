"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { isKey, useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";
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
import { Skeleton } from "@akashic-labs/ui-web/skeleton";

import { authClient } from "~/lib/auth/client";
import { auth } from "~/modules/auth/lib/api";
import {
  SettingsCard,
  SettingsCardContent,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";

export const Passkeys = () => {
  const { t, i18n } = useTranslation(["auth", "common"]);

  const { data: session } = authClient.useSession();
  const userId = session?.user.id ?? "";

  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    ...auth.queries.passkeys.getAll,
    enabled: !!userId,
  });

  const passkeys = data ?? [];

  const add = useMutation({
    ...auth.mutations.passkeys.add,
    onSuccess: async (_, __) => {
      await queryClient.invalidateQueries(auth.queries.passkeys.getAll);
      toast.success(t("account.passkeys.add.success"));
    },
  });

  const remove = useMutation({
    ...auth.mutations.passkeys.delete,
    onSuccess: async (_, __) => {
      await queryClient.invalidateQueries(auth.queries.passkeys.getAll);
      toast.success(t("account.passkeys.remove.success"));
    },
  });

  return (
    <SettingsCard>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("account.passkeys.title")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("account.passkeys.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <SettingsCardContent className="space-y-4">
        {isLoading && <Skeleton className="h-24" />}

        {passkeys.length > 0 && (
          <ul className="overflow-hidden rounded-md border">
            {passkeys.map((passkey) => {
              return (
                <li
                  key={passkey.id}
                  className="flex min-w-0 items-center gap-3 border-b px-4 py-3 last:border-b-0"
                >
                  <Icons.Key className="size-6 shrink-0" />

                  <div className="mr-auto grid grid-cols-1">
                    <span className="truncate text-sm font-medium capitalize">
                      {isKey(
                        `account.passkeys.type.${passkey.deviceType}`,
                        i18n,
                      )
                        ? t(`account.passkeys.type.${passkey.deviceType}`)
                        : passkey.deviceType}
                    </span>
                    <span className="text-muted-foreground truncate text-xs">
                      {t("account.passkeys.addedAt", {
                        date: passkey.createdAt.toLocaleDateString(
                          i18n.language,
                        ),
                      })}
                    </span>
                  </div>

                  <ConfirmModal
                    onConfirm={() => remove.mutate({ id: passkey.id })}
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      disabled={remove.isPending}
                      className="shrink-0"
                    >
                      <span className="sr-only">
                        {t("account.passkeys.remove.cta")}
                      </span>
                      {remove.isPending &&
                      remove.variables.id === passkey.id ? (
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

        {!isLoading && (
          <Button
            variant="outline"
            className="w-full gap-2"
            disabled={add.isPending}
            onClick={() => add.mutate()}
          >
            {add.isPending ? (
              <Icons.Loader2 className="size-4 animate-spin" />
            ) : (
              <>
                <Icons.Plus className="size-4" />
                {t("account.passkeys.add.cta")}
              </>
            )}
          </Button>
        )}
      </SettingsCardContent>

      <SettingsCardFooter>{t("account.passkeys.info")}</SettingsCardFooter>
    </SettingsCard>
  );
};

const ConfirmModal = ({
  children,
  onConfirm,
}: {
  children: React.ReactNode;
  onConfirm: () => void;
}) => {
  const { t } = useTranslation(["common", "auth"]);

  return (
    <Modal>
      <ModalTrigger asChild>{children}</ModalTrigger>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>{t("account.passkeys.remove.cta")}</ModalTitle>
          <ModalDescription className="whitespace-pre-line">
            {t("account.passkeys.remove.disclaimer")}
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
