export const EmailProvider = {
  RESEND: "resend",
  PLUNK: "plunk",
  POSTMARK: "postmark",
  NODEMAILER: "nodemailer",
  SENDGRID: "sendgrid",
} as const;

export type EmailProvider = (typeof EmailProvider)[keyof typeof EmailProvider];

export * from "./templates";
