import { Hono } from "hono";

import {
  getObjectUrlSchema,
  getUploadUrl,
  getSignedUrl,
  getPublicUrl,
  getDeleteUrl,
} from "@akashic-labs/storage/server";

import { enforceAuth, validate } from "../../middleware";

export const storageRouter = new Hono()
  .get(
    "/upload",
    enforceAuth,
    validate("query", getObjectUrlSchema),
    async (c) => c.json(await getUploadUrl(c.req.valid("query"))),
  )
  .get("/public", validate("query", getObjectUrlSchema), async (c) =>
    c.json(await getPublicUrl(c.req.valid("query"))),
  )
  .get(
    "/signed",
    enforceAuth,
    validate("query", getObjectUrlSchema),
    async (c) => c.json(await getSignedUrl(c.req.valid("query"))),
  )
  .get(
    "/delete",
    enforceAuth,
    validate("query", getObjectUrlSchema),
    async (c) => c.json(await getDeleteUrl(c.req.valid("query"))),
  );
