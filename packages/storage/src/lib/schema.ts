import * as z from "zod";

import { env } from "../env";

export const getObjectUrlSchema = z.object({
  path: z.string(),
  bucket: z
    .string()
    .optional()
    .default(env.S3_BUCKET ?? ""),
});

export type GetObjectUrlInput = z.input<typeof getObjectUrlSchema>;
