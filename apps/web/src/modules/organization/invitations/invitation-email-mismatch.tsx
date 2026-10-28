import { Trans } from "@akashic-labs/i18n";
import { getTranslation } from "@akashic-labs/i18n/server";
import { buttonVariants } from "@akashic-labs/ui-web/button";

import { pathsConfig } from "~/config/paths";
import { AuthHeader } from "~/modules/auth/layout/header";
import { TurboLink } from "~/modules/common/turbo-link";

interface InvitationEmailMismatchProps {
  readonly invitationId: string;
  readonly email: string;
}

export const InvitationEmailMismatch = async ({
  invitationId,
  email,
}: InvitationEmailMismatchProps) => {
  const { t } = await getTranslation({ ns: ["organization"] });

  const searchParams = new URLSearchParams();
  searchParams.set("invitationId", invitationId);
  searchParams.set("email", email);
  searchParams.set(
    "redirectTo",
    `${pathsConfig.auth.join}?${searchParams.toString()}`,
  );

  return (
    <>
      <AuthHeader
        title={t("invitations.emailMismatch.title")}
        description={
          <Trans
            i18nKey="invitations.emailMismatch.description"
            ns="organization"
            values={{ email }}
            components={{ bold: <strong /> }}
          />
        }
      />

      <div className="flex flex-col gap-2">
        <TurboLink
          href={`${pathsConfig.auth.login}?${searchParams.toString()}`}
          className={buttonVariants({ size: "lg" })}
        >
          {t("invitations.emailMismatch.cta", { email })}
        </TurboLink>

        <TurboLink
          href={pathsConfig.dashboard.user.index}
          className={buttonVariants({ variant: "outline", size: "lg" })}
        >
          {t("invitations.emailMismatch.skip")}
        </TurboLink>
      </div>
    </>
  );
};
