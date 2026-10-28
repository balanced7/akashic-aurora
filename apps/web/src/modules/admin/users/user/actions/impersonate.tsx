import { useMutation } from "@tanstack/react-query";

import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { pathsConfig } from "~/config/paths";
import { admin } from "~/modules/admin/lib/api";

interface ImpersonateProps {
  readonly id: string;
}

export const Impersonate = ({ id }: ImpersonateProps) => {
  const { t } = useTranslation("common");

  const impersonate = useMutation({
    ...admin.mutations.users.impersonate,
    onSuccess: () => {
      window.open(pathsConfig.index, "_blank");
    },
  });

  const isPending =
    impersonate.isPending && impersonate.variables.userId === id;

  return (
    <Button
      variant="secondary"
      onClick={() => impersonate.mutate({ userId: id })}
      disabled={isPending}
    >
      {isPending ? (
        <Icons.Loader2 className="animate-spin" />
      ) : (
        <Icons.VenetianMask />
      )}
      {t("impersonate")}
    </Button>
  );
};
