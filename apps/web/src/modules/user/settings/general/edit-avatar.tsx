"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { memo } from "react";
import { toast } from "sonner";

import { useTranslation } from "@akashic-labs/i18n";

import {
  AvatarForm,
  AvatarFormErrorMessage,
  AvatarFormInput,
  AvatarFormPreview,
  AvatarFormRemoveButton,
} from "~/modules/common/avatar-form";
import {
  SettingsCard,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";

import { user } from "../../lib/api";

import type { User } from "@akashic-labs/auth";

interface EditAvatarProps {
  readonly user: User;
}

export const EditAvatar = memo<EditAvatarProps>((props) => {
  const { t } = useTranslation(["common", "validation", "auth"]);

  const router = useRouter();

  const updateUser = useMutation(user.mutations.update);

  return (
    <SettingsCard>
      <SettingsCardHeader className="block">
        <AvatarForm
          id={props.user.id}
          image={props.user.image}
          update={(image) => updateUser.mutateAsync({ image })}
        >
          <div className="relative float-right">
            <AvatarFormInput
              onUpload={() => {
                toast.success(t("account.avatar.update.success"));
                router.refresh();
              }}
            >
              <AvatarFormPreview />
            </AvatarFormInput>

            <AvatarFormRemoveButton
              onRemove={() => {
                toast.success(t("account.avatar.remove.success"));
                router.refresh();
              }}
            />
          </div>
          <SettingsCardTitle>{t("avatar")}</SettingsCardTitle>
          <SettingsCardDescription className="py-1.5 whitespace-pre-line">
            {t("account.avatar.description")}
          </SettingsCardDescription>

          <AvatarFormErrorMessage className="mt-1" />
        </AvatarForm>
      </SettingsCardHeader>

      <SettingsCardFooter>{t("account.avatar.info")}</SettingsCardFooter>
    </SettingsCard>
  );
});

EditAvatar.displayName = "EditAvatar";
