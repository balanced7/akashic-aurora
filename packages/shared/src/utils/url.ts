import { wildcardMatch } from "./wildcard-match";

const isExternal = (url: string) =>
  ["http", "https", "mailto", "tel", "//", "www"].some((protocol) =>
    url.startsWith(protocol),
  );

const getOrigin = (url: string) => {
  try {
    const parsedUrl = new URL(url);
    // For custom URL schemes (like exp://), the origin property returns the string "null"
    // instead of null. We need to handle this case and return null so the fallback logic works.
    return parsedUrl.origin === "null" ? null : parsedUrl.origin;
  } catch {
    return null;
  }
};

const getProtocol = (url: string) => {
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.protocol;
  } catch {
    return null;
  }
};

const getHost = (url: string) => {
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.host;
  } catch {
    return null;
  }
};

const mergeSearchParams = (
  target: URL,
  source: URL,
  options?: { overwrite?: boolean; replace?: boolean },
) => {
  const overwrite = options?.overwrite ?? false;
  const replace = options?.replace ?? false;

  if (replace) {
    target.search = source.search;
    return;
  }

  source.searchParams.forEach((value, key) => {
    if (overwrite || !target.searchParams.has(key)) {
      target.searchParams.set(key, value);
    }
  });
};

const matchesPattern = (url: string, pattern: string): boolean => {
  if (url.startsWith("/")) {
    return false;
  }
  if (pattern.includes("*")) {
    // For protocol-specific wildcards, match the full origin
    if (pattern.includes("://")) {
      return wildcardMatch(pattern)(getOrigin(url) ?? url);
    }
    const host = getHost(url);
    if (!host) {
      return false;
    }
    return wildcardMatch(pattern)(host);
  }

  const protocol = getProtocol(url);
  return protocol === "http:" || protocol === "https:" || !protocol
    ? pattern === getOrigin(url)
    : url.startsWith(pattern);
};

export {
  matchesPattern,
  getOrigin,
  getProtocol,
  getHost,
  mergeSearchParams,
  isExternal,
};
