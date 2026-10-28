import { headers } from "next/headers";
import { cache } from "react";

import { auth } from "@akashic-labs/auth/server";

const getHeaders = async () => {
  const newHeaders = new Headers(await headers());
  newHeaders.set("x-client-platform", "web-server");
  return newHeaders;
};

export const getSession = cache(async () => {
  const data = await auth.api.getSession({
    headers: await getHeaders(),
  });

  return {
    session: data?.session ?? null,
    user: data?.user ?? null,
  };
});

export const getOrganization = cache(
  async ({ id, slug }: { slug?: string; id?: string }) => {
    try {
      return await auth.api.getFullOrganization({
        query: {
          organizationId: id,
          organizationSlug: slug,
        },
        headers: await getHeaders(),
      });
    } catch (error) {
      console.error(error);
      return null;
    }
  },
);

export const getInvitation = cache(async ({ id }: { id: string }) => {
  try {
    return await auth.api.getInvitation({
      query: {
        id,
      },
      headers: await getHeaders(),
    });
  } catch {
    return null;
  }
});

export const getUser = cache(async ({ id }: { id: string }) => {
  try {
    return await auth.api.getUser({
      query: { id },
      headers: await getHeaders(),
    });
  } catch {
    return null;
  }
});
