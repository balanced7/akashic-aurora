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

type Props = EmailVariables[typeof EmailTemplate.CHANGE_EMAIL] &
  CommonEmailProps;

export const ChangeEmail = async ({ url, locale, newEmail }: Props) => {
  const { t } = await getTranslation({ locale, ns: "auth" });
  const origin = getOrigin(url);

  return (
    <Layout origin={origin} locale={locale}>
      <Preview>{t("account.email.change.email.preview", { newEmail })}</Preview>
      <Heading className="leading-tight tracking-tight">
        {t("account.email.change.email.subject")}
      </Heading>

      <Text>
        <Trans
          ns="auth"
          i18nKey="account.email.change.email.body"
          values={{ newEmail }}
          components={{
            bold: <strong />,
          }}
        />
      </Text>
      <Button href={url}>{t("account.email.change.email.cta")}</Button>

      <Text>{t("account.email.change.email.or")}</Text>

      <code className="border-border bg-muted inline-block rounded-md border border-solid px-5 py-3.5 font-mono text-xs">
        {url}
      </code>

      <Text className="text-muted-foreground">
        {t("account.email.change.email.disclaimer")}
      </Text>
    </Layout>
  );
};

ChangeEmail.subject = async ({ locale }: CommonEmailProps) => {
  const { t } = await getTranslation({ locale, ns: "auth" });
  return t("account.email.change.email.subject");
};

ChangeEmail.PreviewProps = {
  url: "http://localhost:3090/api/auth/verify-email?token=123&callbackURL=/dashboard/settings",
  locale: "en",
  newEmail: "john@doe.com",
};

export default ChangeEmail;
