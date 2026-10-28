import { describe, expect, it } from "vitest";

import { MemberRole, UserRole } from "../../types";
import {
  generateName,
  getAllRolesAtOrAbove,
  getAllRolesAtOrBelow,
  getUrl,
  hasAdminPermission,
} from "../utils";

import type { User } from "../../types";

const BASE_URL = "http://localhost:3090";

describe("getUrl", () => {
  it("should use x-url header if present", () => {
    const request = new Request(BASE_URL, {
      headers: { "x-url": "https://custom-url.com/path" },
    });
    const url = getUrl({ request });
    expect(url.toString()).toBe("https://custom-url.com/path");
  });

  it("should merge params from passed url into x-url", () => {
    const request = new Request(BASE_URL, {
      headers: { "x-url": "https://custom.com?foo=bar" },
    });
    // mergeSearchParams with overwrite: false (default behavior for x-url branch)
    const url = getUrl({
      request,
      url: "https://ignored.com?baz=qux&foo=new",
    });
    // Should preserve foo=bar from x-url, add baz=qux
    expect(url.searchParams.get("foo")).toBe("bar");
    expect(url.searchParams.get("baz")).toBe("qux");
    expect(url.origin).toBe("https://custom.com");
  });

  it("should use expo-origin header if present (mobile)", () => {
    const request = new Request(BASE_URL, {
      headers: { "expo-origin": "exp://192.168.1.1:8081" },
    });
    const url = getUrl({ request });
    expect(url.toString()).toBe("exp://192.168.1.1:8081");
  });

  it("should replace params from passed url into expo-origin", () => {
    const request = new Request(BASE_URL, {
      headers: { "expo-origin": "exp://host" },
    });
    const url = getUrl({
      request,
      url: "https://ignored.com?foo=bar",
    });
    // Mobile branch uses mergeSearchParams with replace: true
    expect(url.searchParams.get("foo")).toBe("bar");
    expect(url.protocol).toBe("exp:");
    expect(url.host).toBe("host");
  });

  it("should fallback to request url for web", () => {
    const request = new Request("https://web.com/current");
    const url = getUrl({ request });
    expect(url.toString()).toBe("https://web.com/current");
  });

  it("should use provided url for web if no headers", () => {
    const request = new Request("https://web.com");
    const url = getUrl({ request, url: "https://target.com/page" });
    expect(url.toString()).toBe("https://target.com/page");
  });

  it("should append type param if provided", () => {
    const request = new Request("https://web.com");
    const url = getUrl({ request, type: "invite" });
    expect(url.searchParams.get("type")).toBe("invite");
  });
});

describe("generateName", () => {
  it("should generate name from email", () => {
    expect(generateName("john.doe@example.com")).toBe("john.doe");
  });

  it.each([[undefined, null, "john.doe@example.com"]])(
    "should fallback to Anonymous if email is empty",
    (email) => {
      expect(generateName(email)).toBe("Anonymous");
    },
  );
});

describe("getAllRolesAtOrBelow", () => {
  it.each([
    [MemberRole.OWNER, [MemberRole.MEMBER, MemberRole.ADMIN, MemberRole.OWNER]],
    [MemberRole.MEMBER, [MemberRole.MEMBER]],
  ])("should return correct roles for %s", (inputRole, expectedRoles) => {
    const roles = getAllRolesAtOrBelow(inputRole);
    expect(roles).toEqual(expectedRoles);
  });
});

describe("getAllRolesAtOrAbove", () => {
  it.each([
    [MemberRole.OWNER, [MemberRole.OWNER]],
    [
      MemberRole.MEMBER,
      [MemberRole.MEMBER, MemberRole.ADMIN, MemberRole.OWNER],
    ],
  ])("should return correct roles for %s", (inputRole, expectedRoles) => {
    const roles = getAllRolesAtOrAbove(inputRole);
    expect(roles).toEqual(expectedRoles);
  });
});

describe("hasAdminPermission", () => {
  it("should return true if user has ADMIN role", () => {
    const user = { role: UserRole.ADMIN } as User;
    expect(hasAdminPermission(user)).toBe(true);
  });

  it("should return true if user has multiple roles including ADMIN", () => {
    const user = { role: `${UserRole.USER},${UserRole.ADMIN}` } as User;
    expect(hasAdminPermission(user)).toBe(true);
  });

  it("should return false if user does not have ADMIN role", () => {
    const user = { role: UserRole.USER } as User;
    expect(hasAdminPermission(user)).toBe(false);
  });

  it("should return false if user is missing role", () => {
    const user = {} as User;
    expect(hasAdminPermission(user)).toBe(false);
  });
});
