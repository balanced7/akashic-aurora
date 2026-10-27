import * as z from "zod";

export const MAX_MESSAGE_LENGTH = 4000;

export const contactFormSchema = z.object({
  name: z.string().min(2),
  email: z.email().max(254),
  message: z.string().min(10).max(MAX_MESSAGE_LENGTH),
});

export type ContactFormPayload = z.infer<typeof contactFormSchema>;
