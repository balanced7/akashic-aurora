import * as z from "zod";

export const sortSchema = z.object({
  id: z.string(),
  desc: z.boolean().optional().default(false),
});

export type SortPayload = z.infer<typeof sortSchema>;
