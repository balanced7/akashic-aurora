import { Hono } from "hono";

import { ERROR_MESSAGES } from "@akashic-labs/auth";
import { auth } from "@akashic-labs/auth/server";
import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException, isHttpStatus } from "@akashic-labs/shared/utils";

import type { AuthErrorCode } from "@akashic-labs/auth";

export const authRouter = new Hono().on(["GET", "POST"], "*", async (c) => {
  const res = await auth.handler(c.req.raw);

  if (["2", "3"].includes(res.status.toString().slice(0, 1))) {
    return res;
  }

  const json = (await res.json()) as { code: AuthErrorCode; message: string };

  throw new HttpException(
    isHttpStatus(res.status)
      ? res.status
      : HttpStatusCode.INTERNAL_SERVER_ERROR,
    {
      code: ERROR_MESSAGES[json.code],
    },
  );
});
