import { send } from "./providers";
import { getTemplate } from "./templates";

import type { EmailTemplate, EmailVariables } from "./types";

const sendEmail = async <T extends EmailTemplate>({
  to,
  template,
  locale,
  variables,
}: {
  to: string;
  template: T;
  variables: EmailVariables[T];
  locale?: string;
}) => {
  const { html, text, subject } = await getTemplate({
    id: template,
    variables,
    locale,
  });

  return send({ to, subject, html, text });
};

export { sendEmail };
