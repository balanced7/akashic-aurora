import { getTranslation } from "@akashic-labs/i18n/server";
import { buttonVariants } from "@akashic-labs/ui-web/button";

import { pathsConfig } from "~/config/paths";
import { AuthHeader } from "~/modules/auth/layout/header";
import { TurboLink } from "~/modules/common/turbo-link";

export const InvitationExpired = async () => {
  const { t } = await getTranslation({ ns: ["organization"] });

  return (
    <>
      <AuthHeader
        title={t("invitations.expired.title")}
        description={t("invitations.expired.description")}
      />
      <TurboLink
        href={pathsConfig.dashboard.user.index}
        className={buttonVariants({
          variant: "outline",
          size: "lg",
        })}
      >
        {t("invitations.expired.cta")}
      </TurboLink>
    </>
  );
};
