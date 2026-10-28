import dayjs from "dayjs";
import * as z from "zod";

import { env } from "../env";
import { makeZodI18nMap } from "../utils";

import { getLocaleFromCookies, initializeServerI18n } from ".";

type LayoutOrPageComponent<Params> = React.ComponentType<Params>;

export function withI18n<Params extends object>(
  Component: LayoutOrPageComponent<Params>,
) {
  return async function I18nServerComponentWrapper(params: Params) {
    const i18n = await initializeServerI18n({
      locale: await getLocaleFromCookies(),
      defaultLocale: env.DEFAULT_LOCALE,
    });
    dayjs.locale(i18n.language);
    z.config({
      localeError: makeZodI18nMap({ t: i18n.t }),
    });

    return <Component {...params} />;
  };
}
