import env from "env.config";

export const getBaseUrl = () => {
  if (typeof window !== "undefined") return window.location.origin;
  if (env.NEXT_PUBLIC_URL) return env.NEXT_PUBLIC_URL;
  if (env.VERCEL_URL) return `https://${env.VERCEL_URL}`;
  // eslint-disable-next-line no-restricted-properties, turbo/no-undeclared-env-vars
  return `http://localhost:${process.env.PORT ?? 3090}`;
};
