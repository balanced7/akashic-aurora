import { authClient } from "~/lib/auth/client";

const KEY = "user";

const queries = {
  invitations: {
    getAll: {
      queryKey: [KEY, "invitations"],
      queryFn: () =>
        authClient.organization.listUserInvitations({
          fetchOptions: { throw: true },
        }),
    },
  },
};

const mutations = {
  delete: {
    mutationKey: [KEY, "delete"],
    mutationFn: (params: Parameters<typeof authClient.deleteUser>[0]) =>
      authClient.deleteUser(params),
  },
  update: {
    mutationKey: [KEY, "update"],
    mutationFn: (params: Parameters<typeof authClient.updateUser>[0]) =>
      authClient.updateUser(params),
  },
};

export const user = {
  queries,
  mutations,
};
