import * as z from "zod";

export const offsetPaginationSchema = z.object({
  page: z.coerce.number().int().default(1),
  perPage: z.coerce.number().int().default(10),
});

export type OffsetPaginationPayload = z.infer<typeof offsetPaginationSchema>;

export const cursorPaginationSchema = z.object({
  cursor: z.string().optional(),
  limit: z.coerce.number().int().default(10),
});

export type CursorPaginationPayload = z.infer<typeof cursorPaginationSchema>;
