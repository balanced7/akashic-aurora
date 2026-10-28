import { Heading, Preview, Row, Column } from "@react-email/components";
import * as React from "react";

import { getTranslation } from "@akashic-labs/i18n/server";

import { Layout } from "./_components/layout/layout";

import type { EmailTemplate } from "../types";
import type { EmailVariables } from "../types";

type Props = EmailVariables[typeof EmailTemplate.CONTACT_FORM];

export const ContactForm = async (props: Props) => {
  const { t } = await getTranslation({ ns: "marketing" });

  return (
    <Layout>
      <Preview>{t("contact.email.subject")}</Preview>
      <Heading className="leading-tight tracking-tight">
        {t("contact.email.body")}
      </Heading>

      {Object.entries(props).map(([key, value]) => (
        <Row key={key}>
          <Column>
            <strong>{key}</strong>: {value}
          </Column>
        </Row>
      ))}
    </Layout>
  );
};

ContactForm.subject = async () => {
  const { t } = await getTranslation({ ns: "marketing" });
  return t("contact.email.subject");
};

ContactForm.PreviewProps = {
  name: "John Doe",
  email: "john.doe@example.com",
  message: "Hello, I'm interested in your services.",
};

export default ContactForm;
