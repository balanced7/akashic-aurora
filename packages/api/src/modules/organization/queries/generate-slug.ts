import { auth } from "@akashic-labs/auth/server";
import { HttpStatusCode } from "@akashic-labs/shared/constants";
import { HttpException, slugify } from "@akashic-labs/shared/utils";

const MAX_ATTEMPTS = 3;

export const generateSlug = async (name: string) => {
  const base = slugify(name, {
    lower: true,
    remove: /[.,'+:()]/g,
  });

  let slug = base;
  let isAvailable = false;

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    let check;
    try {
      check = await auth.api.checkOrganizationSlug({
        body: { slug },
      });
    } catch {
      check = { status: false };
    }

    if (check.status) {
      isAvailable = true;
      break;
    }

    const randomDigits = Math.floor(100000 + Math.random() * 900000).toString();
    slug = `${base}-${randomDigits}`;
  }

  if (!isAvailable) {
    throw new HttpException(HttpStatusCode.BAD_REQUEST, {
      code: "organization:error.slugNotAvailable",
    });
  }

  return { slug };
};
