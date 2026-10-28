"use server";

import { cookies } from "next/headers";

import { config } from "@akashic-labs/i18n";

import type { Locale } from "@akashic-labs/i18n";

export const setLocaleCookie = async (locale: Locale) => {
  const cookieStore = await cookies();
  cookieStore.set(config.cookie, locale);
};
