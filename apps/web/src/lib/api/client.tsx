import { hc } from "hono/client";

import { getBaseUrl } from "./utils";

import type { AppRouter } from "@akashic-labs/api";

export const { api } = hc<AppRouter>(getBaseUrl(), {
  headers: {
    "x-client-platform": "web-client",
  },
  init: {
    credentials: "include",
  },
});
