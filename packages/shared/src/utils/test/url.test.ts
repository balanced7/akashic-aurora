import { describe, expect, it } from "vitest";

import {
  getHost,
  getOrigin,
  getProtocol,
  isExternal,
  matchesPattern,
  mergeSearchParams,
} from "../url";

describe("isExternal", () => {
  it.each([
    ["https://google.com", true],
    ["http://example.com", true],
    ["//cdn.example.com", true],
    ["mailto:user@example.com", true],
    ["/dashboard", false],
    ["about", false],
  ])("should return $expected for url $url", (url, expected) => {
    expect(isExternal(url)).toBe(expected);
  });
});

describe("getOrigin", () => {
  it.each([
    ["https://example.com/path", "https://example.com"],
    ["invalid-url", null],
    ["exp://192.168.1.1:8081", null],
  ])("should return %s for %s", (url, expected) => {
    expect(getOrigin(url)).toBe(expected);
  });
});

describe("getProtocol", () => {
  it.each([
    ["https://example.com", "https:"],
    ["mailto:user@example.com", "mailto:"],
    ["not-a-url", null],
  ])("should return %s for %s", (url, expected) => {
    expect(getProtocol(url)).toBe(expected);
  });
});

describe("getHost", () => {
  it.each([
    ["https://example.com:8080/path", "example.com:8080"],
    ["invalid", null],
  ])("should return %s for %s", (url, expected) => {
    expect(getHost(url)).toBe(expected);
  });
});

describe("mergeSearchParams", () => {
  it("should merge params without overwrite by default", () => {
    const target = new URL("https://example.com?a=1");
    const source = new URL("https://other.com?a=2&b=3");
    mergeSearchParams(target, source);
    expect(target.searchParams.get("a")).toBe("1");
    expect(target.searchParams.get("b")).toBe("3");
  });

  it("should overwrite params if specified", () => {
    const target = new URL("https://example.com?a=1");
    const source = new URL("https://other.com?a=2");
    mergeSearchParams(target, source, { overwrite: true });
    expect(target.searchParams.get("a")).toBe("2");
  });

  it("should replace params if specified", () => {
    const target = new URL("https://example.com?a=1");
    const source = new URL("https://other.com?b=2");
    mergeSearchParams(target, source, { replace: true });
    expect(target.searchParams.has("a")).toBe(false);
    expect(target.searchParams.get("b")).toBe("2");
  });
});

describe("matchesPattern", () => {
  it.each([
    ["/path", "https://example.com", false],
    ["https://sub.example.com", "*.example.com", true],
    ["https://example.com", "https://example.com", true],
    ["https://example.org", "https://example.com", false],
    ["https://example.com/foo", "https://example.com", true],
    ["https://example.com", "https://*", true],
  ])(
    "should return %s when matching %s with pattern %s",
    (url, pattern, expected) => {
      expect(matchesPattern(url, pattern)).toBe(expected);
    },
  );
});
