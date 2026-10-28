import {
  getInvitationsResponseSchema,
  getMembersResponseSchema,
  getOrganizationResponseSchema,
  getUserAccountsResponseSchema,
  getUserInvitationsResponseSchema,
  getUserMembershipsResponseSchema,
  getUserPlansResponseSchema,
} from "@akashic-labs/api/schema";
import { handle } from "@akashic-labs/api/utils";

import { api } from "~/lib/api/client";
import { authClient } from "~/lib/auth/client";

import type { User } from "@akashic-labs/auth";
import type { InferRequestType } from "hono/client";

const KEY = "admin";

const queries = {
  users: {
    get: ({ id }: { id: string }) => ({
      queryKey: [KEY, "users", id],
      queryFn: () =>
        authClient.admin.getUser({
          query: { id },
          fetchOptions: { throw: true },
        }) as Promise<User>,
    }),
    getAccounts: ({
      id,
      ...query
    }: InferRequestType<
      (typeof api.admin.users)[":id"]["accounts"]["$get"]
    >["query"] & { id: string }) => ({
      queryKey: [KEY, "users", id, "accounts", query],
      queryFn: () =>
        handle(api.admin.users[":id"].accounts.$get, {
          schema: getUserAccountsResponseSchema,
        })({
          query,
          param: {
            id,
          },
        }),
    }),
    getPlans: ({
      id,
      ...query
    }: InferRequestType<
      (typeof api.admin.users)[":id"]["plans"]["$get"]
    >["query"] & { id: string }) => ({
      queryKey: [KEY, "users", id, "plans", query],
      queryFn: () =>
        handle(api.admin.users[":id"].plans.$get, {
          schema: getUserPlansResponseSchema,
        })({ query, param: { id } }),
    }),
    getMemberships: ({
      id,
      ...query
    }: InferRequestType<
      (typeof api.admin.users)[":id"]["memberships"]["$get"]
    >["query"] & { id: string }) => ({
      queryKey: [KEY, "users", id, "memberships", query],
      queryFn: () =>
        handle(api.admin.users[":id"].memberships.$get, {
          schema: getUserMembershipsResponseSchema,
        })({ query, param: { id } }),
    }),
    getInvitations: ({
      id,
      ...query
    }: InferRequestType<
      (typeof api.admin.users)[":id"]["invitations"]["$get"]
    >["query"] & { id: string }) => ({
      queryKey: [KEY, "users", id, "invitations", query],
      queryFn: () =>
        handle(api.admin.users[":id"].invitations.$get, {
          schema: getUserInvitationsResponseSchema,
        })({ query, param: { id } }),
    }),
    getSessions: ({ id }: { id: string }) => ({
      queryKey: [KEY, "users", id, "sessions"],
      queryFn: () =>
        authClient.admin.listUserSessions({
          userId: id,
          fetchOptions: { throw: true },
        }),
    }),
  },
  organizations: {
    get: ({ id }: { id: string }) => ({
      queryKey: [KEY, "organizations", id],
      queryFn: () =>
        handle(api.admin.organizations[":id"].$get, {
          schema: getOrganizationResponseSchema,
        })({
          param: { id },
        }),
    }),
    getMembers: ({
      id,
      ...query
    }: InferRequestType<
      (typeof api.admin.organizations)[":id"]["members"]["$get"]
    >["query"] & { id: string }) => ({
      queryKey: [
        ...queries.organizations.get({ id }).queryKey,
        "members",
        query,
      ],
      queryFn: () =>
        handle(api.admin.organizations[":id"].members.$get, {
          schema: getMembersResponseSchema,
        })({
          query,
          param: {
            id,
          },
        }),
    }),
    getInvitations: ({
      id,
      ...query
    }: InferRequestType<
      (typeof api.admin.organizations)[":id"]["invitations"]["$get"]
    >["query"] & { id: string }) => ({
      queryKey: [
        ...queries.organizations.get({ id }).queryKey,
        "invitations",
        query,
      ],
      queryFn: () =>
        handle(api.admin.organizations[":id"].invitations.$get, {
          schema: getInvitationsResponseSchema,
        })({ query, param: { id } }),
    }),
  },
};

const mutations = {
  users: {
    ban: {
      mutationKey: [KEY, "users", "ban"],
      mutationFn: (params: Parameters<typeof authClient.admin.banUser>[0]) =>
        authClient.admin.banUser(params),
    },
    unban: {
      mutationKey: [KEY, "users", "unban"],
      mutationFn: (params: Parameters<typeof authClient.admin.unbanUser>[0]) =>
        authClient.admin.unbanUser(params),
    },
    delete: {
      mutationKey: [KEY, "users", "delete"],
      mutationFn: (params: Parameters<typeof authClient.admin.removeUser>[0]) =>
        authClient.admin.removeUser(params),
    },
    impersonate: {
      mutationKey: [KEY, "users", "impersonate"],
      mutationFn: (
        params: Parameters<typeof authClient.admin.impersonateUser>[0],
      ) => authClient.admin.impersonateUser(params),
    },
    stopImpersonating: {
      mutationKey: [KEY, "users", "impersonate", "stop"],
      mutationFn: () => authClient.admin.stopImpersonating(),
    },
    update: {
      mutationKey: [KEY, "users", "update"],
      mutationFn: (params: Parameters<typeof authClient.admin.updateUser>[0]) =>
        authClient.admin.updateUser(params),
    },
    setPassword: {
      mutationKey: [KEY, "users", "setPassword"],
      mutationFn: (
        params: Parameters<typeof authClient.admin.setUserPassword>[0],
      ) => authClient.admin.setUserPassword(params),
    },
    accounts: {
      delete: {
        mutationKey: [KEY, "users", "accounts", "delete"],
        mutationFn: (
          param: InferRequestType<
            (typeof api.admin.users)[":id"]["accounts"][":accountId"]["$delete"]
          >["param"],
        ) =>
          handle(api.admin.users[":id"].accounts[":accountId"].$delete)({
            param,
          }),
      },
    },
    sessions: {
      revoke: {
        mutationKey: [KEY, "users", "sessions", "revoke"],
        mutationFn: (
          params: Parameters<typeof authClient.admin.revokeUserSession>[0],
        ) => authClient.admin.revokeUserSession(params),
      },
      revokeAll: {
        mutationKey: [KEY, "users", "sessions", "revokeAll"],
        mutationFn: (
          params: Parameters<typeof authClient.admin.revokeUserSessions>[0],
        ) => authClient.admin.revokeUserSessions(params),
      },
    },
  },
  organizations: {
    delete: {
      mutationKey: [KEY, "organizations", "delete"],
      mutationFn: (
        param: InferRequestType<
          (typeof api.admin.organizations)[":id"]["$delete"]
        >["param"],
      ) =>
        handle(api.admin.organizations[":id"].$delete)({
          param,
        }),
    },
    update: {
      mutationKey: [KEY, "organizations", "update"],
      mutationFn: ({
        id,
        ...json
      }: InferRequestType<
        (typeof api.admin.organizations)[":id"]["$patch"]
      >["json"] & { id: string }) =>
        handle(api.admin.organizations[":id"].$patch)({ param: { id }, json }),
    },
    members: {
      remove: {
        mutationKey: [KEY, "organizations", "members", "remove"],
        mutationFn: (
          param: InferRequestType<
            (typeof api.admin.organizations)[":id"]["members"][":memberId"]["$delete"]
          >["param"],
        ) =>
          handle(api.admin.organizations[":id"].members[":memberId"].$delete)({
            param,
          }),
      },
      update: {
        mutationKey: [KEY, "organizations", "members", "update"],
        mutationFn: ({
          id,
          memberId,
          ...json
        }: InferRequestType<
          (typeof api.admin.organizations)[":id"]["members"][":memberId"]["$patch"]
        >["json"] & { id: string; memberId: string }) =>
          handle(api.admin.organizations[":id"].members[":memberId"].$patch)({
            param: { id, memberId },
            json,
          }),
      },
    },
    invitations: {
      delete: {
        mutationKey: [KEY, "organizations", "invitations", "delete"],
        mutationFn: (
          param: InferRequestType<
            (typeof api.admin.organizations)[":id"]["invitations"][":invitationId"]["$delete"]
          >["param"],
        ) =>
          handle(
            api.admin.organizations[":id"].invitations[":invitationId"].$delete,
          )({
            param,
          }),
      },
    },
  },
  customers: {
    delete: {
      mutationKey: [KEY, "customers", "delete"],
      mutationFn: (
        param: InferRequestType<
          (typeof api.admin.customers)[":id"]["$delete"]
        >["param"],
      ) => handle(api.admin.customers[":id"].$delete)({ param }),
    },
    update: {
      mutationKey: [KEY, "customers", "update"],
      mutationFn: ({
        id,
        ...json
      }: InferRequestType<
        (typeof api.admin.customers)[":id"]["$patch"]
      >["json"] & { id: string }) =>
        handle(api.admin.customers[":id"].$patch)({
          param: { id },
          json,
        }),
    },
  },
};

export const admin = {
  queries,
  mutations,
} as const;
