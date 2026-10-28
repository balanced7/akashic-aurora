import nodemailer from "nodemailer";

import { env } from "./env";

import type { EmailProviderStrategy } from "../types";

const from = env.EMAIL_FROM;

const send: EmailProviderStrategy["send"] = async ({
  to,
  subject,
  html,
  text,
}) => {
  const transporter = nodemailer.createTransport({
    host: env.NODEMAILER_HOST,
    port: env.NODEMAILER_PORT,
    auth: {
      user: env.NODEMAILER_USER,
      pass: env.NODEMAILER_PASSWORD,
    },
  });

  await transporter.sendMail({
    from,
    to,
    subject,
    html,
    text,
  });
};

export { send };
