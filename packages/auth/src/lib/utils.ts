import { getOrigin, mergeSearchParams } from "@akashic-labs/shared/utils";

import { MemberRole, UserRole } from "../types";

import type { User } from "../types";

export const getUrl = ({
  request,
  url,
  type,
}: {
  request?: Request;
  url?: string;
  type?: string;
}) => {
  const passedUrl = request?.headers.get("x-url");
  const expoOrigin = request?.headers.get("expo-origin");

  let resultUrl: URL;

  if (passedUrl) {
    // Base on x-url; merge in params from provided `url` without overwriting existing keys
    resultUrl = new URL(passedUrl);
    if (url) {
      const urlObj = new URL(
        url,
        getOrigin(resultUrl.toString()) ?? expoOrigin ?? undefined,
      );
      mergeSearchParams(resultUrl, urlObj, { overwrite: false });
    }
  } else if (expoOrigin) {
    // For Expo/mobile, base on expo-origin; if `url` has a query, adopt it entirely
    resultUrl = new URL(expoOrigin);
    if (url) {
      const targetUrl = new URL(url);
      if (targetUrl.search) {
        mergeSearchParams(resultUrl, targetUrl, { replace: true });
      }
    }
  } else {
    // For web, use the provided URL or fall back to the request URL
    resultUrl = new URL(url ?? request?.url ?? "");
  }

  if (type) {
    resultUrl.searchParams.set("type", type);
  }

  return resultUrl;
};

const hierarchy: MemberRole[] = [
  MemberRole.MEMBER,
  MemberRole.ADMIN,
  MemberRole.OWNER,
];

export const generateName = (email?: string) => {
  return email?.split("@")[0] ?? "Anonymous";
};

export const getAllRolesAtOrBelow = (role: MemberRole): MemberRole[] => {
  const idx = hierarchy.indexOf(role);
  if (idx === -1) return [];

  return hierarchy.slice(0, idx + 1);
};

export const getAllRolesAtOrAbove = (role: MemberRole): MemberRole[] => {
  const idx = hierarchy.indexOf(role);
  if (idx === -1) return [];
  return hierarchy.slice(idx, hierarchy.length);
};

export const hasAdminPermission = (user: User) =>
  user.role?.split(",").includes(UserRole.ADMIN) ?? false;
