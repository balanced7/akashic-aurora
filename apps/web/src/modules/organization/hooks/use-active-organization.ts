"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams, usePathname } from "next/navigation";
import { useEffect, useMemo } from "react";

import { useDebounceCallback } from "@akashic-labs/shared/hooks";

import { pathsConfig } from "~/config/paths";
import { authClient } from "~/lib/auth/client";

import { organization } from "../lib/api";

import type { MemberRole } from "@akashic-labs/auth";

const DEBOUNCE_SET_ACTIVE_MS = 1000;

export const useActiveOrganization = () => {
  const session = authClient.useSession();
  const member = authClient.useActiveMember();

  const pathname = usePathname();
  const params = useParams();
  const slug = params.organization?.toString();

  const allowRefetch = useMemo(
    () => !!(slug ?? pathname.startsWith(pathsConfig.dashboard.user.index)),
    [pathname, slug],
  );

  const { data: activeOrganization, isLoading } = useQuery({
    ...organization.queries.get({ slug: slug ?? "" }),
    enabled: !!slug,
  });

  const setActiveOrganization = useMutation({
    ...organization.mutations.setActive,
    onSuccess: async () => {
      await session.refetch();
    },
  });

  const debouncedSetActiveOrganization = useDebounceCallback(
    setActiveOrganization.mutate,
    DEBOUNCE_SET_ACTIVE_MS,
  );

  const activeMember = useMemo(() => {
    const data =
      member.data ??
      activeOrganization?.members.find(
        (member) => member.userId === session.data?.user.id,
      );
    return data ? { ...data, role: data.role as MemberRole } : null;
  }, [member.data, activeOrganization, session.data]);

  const activeOrganizationId = activeOrganization?.id ?? null;
  const memberOrganizationId = member.data?.organizationId ?? null;
  const sessionActiveOrganizationId =
    session.data?.session.activeOrganizationId ?? null;

  const shouldRefetchMember = useMemo(() => {
    return (
      !member.isPending &&
      !member.isRefetching &&
      memberOrganizationId !== activeOrganizationId &&
      allowRefetch
    );
  }, [
    member.isPending,
    member.isRefetching,
    memberOrganizationId,
    activeOrganizationId,
    allowRefetch,
  ]);

  useEffect(() => {
    if (shouldRefetchMember) {
      void member.refetch();
    }
  }, [member, shouldRefetchMember]);

  const shouldUpdateActiveOrganization = useMemo(() => {
    return (
      !session.isPending &&
      !!session.data &&
      !(isLoading && !activeOrganizationId) &&
      sessionActiveOrganizationId !== activeOrganizationId &&
      allowRefetch
    );
  }, [
    session.isPending,
    session.data,
    isLoading,
    activeOrganizationId,
    sessionActiveOrganizationId,
    allowRefetch,
  ]);

  useEffect(() => {
    if (shouldUpdateActiveOrganization) {
      debouncedSetActiveOrganization({
        organizationId: activeOrganizationId,
      });
    }
  }, [
    shouldUpdateActiveOrganization,
    activeOrganizationId,
    debouncedSetActiveOrganization,
  ]);

  return {
    activeOrganization,
    activeMember,
  };
};
