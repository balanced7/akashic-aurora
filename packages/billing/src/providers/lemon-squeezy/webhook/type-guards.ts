import * as z from "zod";

const metaSchema = z.object({
  meta: z.object({
    event_name: z.string(),
    custom_data: z.object({
      user_id: z.string(),
    }),
  }),
});

/**
 * Typeguard to check if the object has a 'meta' property
 * and that the 'meta' property has the correct shape.
 */
export function webhookHasMeta(
  obj: unknown,
): obj is z.infer<typeof metaSchema> {
  return metaSchema.safeParse(obj).success;
}

const dataSchema = z.object({
  data: z.object({
    id: z.string(),
  }),
});

/**
 * Typeguard to check if the object has a 'data' property and the correct shape.
 *
 * @param obj - The object to check.
 * @returns True if the object has a 'data' property.
 */
export function webhookHasData(
  obj: unknown,
): obj is z.infer<typeof dataSchema> {
  return dataSchema.safeParse(obj).success;
}
