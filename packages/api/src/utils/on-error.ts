import * as z from "zod";

import { isKey } from "@akashic-labs/i18n";
import { getTranslation } from "@akashic-labs/i18n/server";
import { getStatusCode } from "@akashic-labs/shared/utils";

import type { Context } from "hono";

const errorSchema = z.object({
  code: z.string().optional(),
  message: z.string(),
});

const isError = (e: unknown): e is z.infer<typeof errorSchema> => {
  return errorSchema.safeParse(e).success;
};

export const onError = async (
  e: unknown,
  c?: Context<{
    Bindings: { NODE_ENV: string };
    Variables: { locale: string };
  }>,
) => {
  const { t, i18n } = await getTranslation({
    locale: c?.var.locale,
    request: c?.req.raw,
  });
  const details = {
    status: getStatusCode(e),
    headers: {
      "Content-Type": "application/json",
    },
  };

  const timestamp = new Date().toISOString();
  const path = c?.req.raw.url ? new URL(c.req.raw.url).pathname : "/api";

  if (isError(e)) {
    console.log(e.code, e.message);

    return new Response(
      JSON.stringify({
        code: e.code,
        message: e.message
          ? e.message
          : e.code && isKey(e.code, i18n)
            ? t(e.code)
            : ((e.message || e.code) ?? t("common:error.general")),
        status: details.status,
        timestamp,
        path,
      }),
      details,
    );
  }

  return new Response(
    JSON.stringify({
      code: "common:error.general",
      message: t("common:error.general"),
      status: details.status,
      path,
    }),
    details,
  );
};
