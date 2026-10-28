import env from "env.config";

export const appConfig = {
  name: env.NEXT_PUBLIC_PRODUCT_NAME,
  url: env.NEXT_PUBLIC_URL,
  locale: env.NEXT_PUBLIC_DEFAULT_LOCALE,
  theme: {
    mode: env.NEXT_PUBLIC_THEME_MODE,
    color: env.NEXT_PUBLIC_THEME_COLOR,
  },
} as const;
