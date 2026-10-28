import { Heading, Preview, Text } from "@react-email/components";
import * as React from "react";

import { Trans } from "@akashic-labs/i18n";
import { getTranslation } from "@akashic-labs/i18n/server";
import { getOrigin } from "@akashic-labs/shared/utils";

import { Button } from "../_components/button";
import { Layout } from "../_components/layout/layout";

import type {
  EmailVariables,
  EmailTemplate,
  CommonEmailProps,
} from "../../types";

type Props = EmailVariables[typeof EmailTemplate.ORGANIZATION_INVITATION] &
  CommonEmailProps;

export const OrganizationInvitation = async ({
  url,
  inviter,
  organization,
  locale,
}: Props) => {
  const { t } = await getTranslation({ locale, ns: "organization" });
  const origin = getOrigin(url);

  return (
    <Layout origin={origin} locale={locale}>
      <Preview>{t("members.invite.email.preview", { inviter })}</Preview>
      <Heading className="leading-tight tracking-tight">
        {t("members.invite.email.subject")}
      </Heading>

      <Text>
        <Trans
          i18nKey="members.invite.email.body"
          ns="organization"
          values={{ inviter, organization }}
          components={{
            bold: <strong />,
          }}
        />
      </Text>

      <Button href={url}>
        {t("members.invite.email.cta", { organization })}
      </Button>

      <Text>{t("members.invite.email.or")}</Text>

      <code className="border-border bg-muted inline-block rounded-md border border-solid px-5 py-3.5 font-mono text-xs">
        {url}
      </code>

      <Text className="text-muted-foreground">
        {t("members.invite.email.disclaimer")}
      </Text>
    </Layout>
  );
};

OrganizationInvitation.subject = async ({ locale }: CommonEmailProps) => {
  const { t } = await getTranslation({ locale, ns: "organization" });
  return t("members.invite.email.subject");
};

OrganizationInvitation.PreviewProps = {
  url: "http://localhost:3090/auth/join?invitationId=h4zI2pKJrQkP5NQljdA8W57wG0V8LHrv",
  locale: "en",
  inviter: "John Doe",
  organization: "Akashic Labs Inc",
};

export default OrganizationInvitation;
