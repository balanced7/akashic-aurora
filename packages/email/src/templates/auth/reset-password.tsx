import { Heading, Preview, Text } from "@react-email/components";
import * as React from "react";

import { getTranslation } from "@akashic-labs/i18n/server";
import { getOrigin } from "@akashic-labs/shared/utils";

import { Button } from "../_components/button";
import { Layout } from "../_components/layout/layout";

import type {
  EmailVariables,
  EmailTemplate,
  CommonEmailProps,
} from "../../types";

type Props = EmailVariables[typeof EmailTemplate.CONFIRM_EMAIL] &
  CommonEmailProps;

export const ResetPassword = async ({ url, locale }: Props) => {
  const { t } = await getTranslation({ locale, ns: "auth" });
  const origin = getOrigin(url);

  return (
    <Layout origin={origin}>
      <Preview>{t("account.password.update.email.preview")}</Preview>
      <Heading className="leading-tight tracking-tight">
        {t("account.password.update.email.subject")}
      </Heading>

      <Text>{t("account.password.update.email.body")}</Text>

      <Button href={url}>{t("account.password.update.email.cta")}</Button>

      <Text>{t("account.password.update.email.or")}</Text>

      <code className="border-border bg-muted inline-block rounded-md border border-solid px-5 py-3.5 font-mono text-xs">
        {url}
      </code>

      <Text className="text-muted-foreground">
        {t("account.password.update.email.disclaimer")}
      </Text>
    </Layout>
  );
};

ResetPassword.subject = async ({ locale }: CommonEmailProps) => {
  const { t } = await getTranslation({ locale, ns: "auth" });
  return t("account.password.update.email.subject");
};

ResetPassword.PreviewProps = {
  url: "http://localhost:3090/api/auth/reset-password/KwiyWf9xsTrfndZY5a0stg4p?callbackURL=/auth/password/update",
  locale: "en",
};

export default ResetPassword;
