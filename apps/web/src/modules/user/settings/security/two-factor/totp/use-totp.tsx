import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { create } from "zustand";

import { useTranslation } from "@akashic-labs/i18n";

import { auth } from "~/modules/auth/lib/api";

import { useBackupCodes } from "../backup-codes/use-backup-codes";

const useUri = create<{
  uri: string;
  setUri: (uri: string) => void;
}>((set) => ({
  uri: "",
  setUri: (uri) => set({ uri }),
}));

export const useTotp = () => {
  const { t } = useTranslation(["auth"]);
  const { uri, setUri } = useUri();
  const { codes, setCodes } = useBackupCodes();

  const getUri = useMutation({
    ...auth.mutations.twoFactor.totp.getUri,
    onSuccess: async ({ totpURI }, data) => {
      setUri(totpURI);
      if (!codes.length) {
        const backupCodes =
          await auth.mutations.twoFactor.backupCodes.generate.mutationFn(data);

        setCodes(backupCodes.backupCodes);
      }
    },
  });

  const verify = useMutation({
    ...auth.mutations.twoFactor.totp.verify,
    onSuccess: (_, __) => {
      toast.success(t("account.twoFactor.totp.success"));
    },
  });

  return { uri, setUri, verify, getUri };
};
