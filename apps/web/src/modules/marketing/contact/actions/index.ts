"use server";

import env from "env.config";

import { EmailTemplate } from "@akashic-labs/email";
import { sendEmail } from "@akashic-labs/email/server";
import { getTranslation } from "@akashic-labs/i18n/server";

import type { ContactFormPayload } from "../utils/schema";

export const sendContactForm = async (data: ContactFormPayload) => {
  try {
    await sendEmail({
      to: env.CONTACT_EMAIL,
      template: EmailTemplate.CONTACT_FORM,
      variables: data,
    });
    return { error: null };
  } catch (e) {
    if (e instanceof Error) {
      return { error: e.message };
    }

    const { t } = await getTranslation({ ns: "common" });
    return { error: t("error.general") };
  }
};
