import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import { useTranslation } from "@akashic-labs/i18n";

import { authClient } from "~/lib/auth/client";
import { auth } from "~/modules/auth/lib/api";

export const useTwoFactor = () => {
  const { data } = authClient.useSession();
  const { t } = useTranslation("auth");

  const enabled = data?.user.twoFactorEnabled ?? false;

  const enable = useMutation(auth.mutations.twoFactor.enable);

  const disable = useMutation({
    ...auth.mutations.twoFactor.disable,
    onSuccess: (_, __) => {
      toast.success(t("account.twoFactor.disable.success"));
    },
  });

  return { enabled, enable, disable };
};
