import { render } from "@react-email/render";

import { EmailTemplate } from "../types";

import ChangeEmail from "./auth/change-email";
import { ConfirmEmail } from "./auth/confirm-email";
import DeleteAccount from "./auth/delete-account";
import { MagicLink } from "./auth/magic-link";
import { OrganizationInvitation } from "./auth/organization-invitation";
import { ResetPassword } from "./auth/reset-password";
import ContactForm from "./contact-form";

import type { CommonEmailProps, EmailVariables } from "../types";

interface EmailTemplateComponent<T extends EmailTemplate> {
  (
    props: EmailVariables[T] & CommonEmailProps,
  ): Promise<React.ReactElement> | React.ReactElement;
  subject: ((props: CommonEmailProps) => Promise<string> | string) | string;
}

export const templates: {
  [K in EmailTemplate]: EmailTemplateComponent<K>;
} = {
  [EmailTemplate.RESET_PASSWORD]: ResetPassword,
  [EmailTemplate.MAGIC_LINK]: MagicLink,
  [EmailTemplate.CONFIRM_EMAIL]: ConfirmEmail,
  [EmailTemplate.DELETE_ACCOUNT]: DeleteAccount,
  [EmailTemplate.CHANGE_EMAIL]: ChangeEmail,
  [EmailTemplate.ORGANIZATION_INVITATION]: OrganizationInvitation,
  [EmailTemplate.CONTACT_FORM]: ContactForm,
} as const;

export const getTemplate = async <T extends EmailTemplate>({
  id,
  locale,
  variables,
}: {
  id: T;
  variables: EmailVariables[T];
  locale?: string;
}) => {
  const template = templates[id];
  const subject =
    typeof template.subject === "function"
      ? await template.subject({ locale })
      : template.subject;
  const email = await template({ ...variables, locale });

  const html = await render(email);
  const text = await render(email, { plainText: true });

  return { html, text, subject };
};
