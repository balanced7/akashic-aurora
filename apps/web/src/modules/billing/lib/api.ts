import { handle } from "@akashic-labs/api/utils";

import { api } from "~/lib/api/client";

import type { InferRequestType } from "hono/client";

const KEY = "billing";

const queries = {
  customer: {
    get: {
      queryKey: [KEY, "customer"],
      queryFn: () => handle(api.billing.customer.$get)(),
    },
  },
};

const mutations = {
  portal: {
    get: {
      mutationKey: [KEY, "portal"],
      mutationFn: (data: InferRequestType<typeof api.billing.portal.$get>) =>
        handle(api.billing.portal.$get)(data),
    },
  },
  checkout: {
    create: {
      mutationKey: [KEY, "checkout"],
      mutationFn: (data: InferRequestType<typeof api.billing.checkout.$post>) =>
        handle(api.billing.checkout.$post)(data),
    },
  },
};

export const billing = {
  queries,
  mutations,
};
