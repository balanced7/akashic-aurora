import { lemonSqueezySetup } from "@lemonsqueezy/lemonsqueezy.js";

import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException } from "@akashic-labs/shared/utils";

import { env } from "./env";

export const setup = () => {
  return lemonSqueezySetup({
    apiKey: env.LEMON_SQUEEZY_API_KEY,
    onError: (error) => {
      console.error(error);
      throw new HttpException(HttpStatusCode.INTERNAL_SERVER_ERROR, {
        code: "billing:error.lemonSqueezy",
        message: error.message,
      });
    },
  });
};
