import { authClient } from "~/lib/auth/client";

const KEY = "auth";

const queries = {
  sessions: {
    getAll: {
      queryKey: [KEY, "sessions"],
      queryFn: () =>
        authClient.listSessions({
          fetchOptions: {
            throw: true,
          },
        }),
    },
  },
  accounts: {
    getAll: {
      queryKey: [KEY, "accounts"],
      queryFn: () => authClient.listAccounts({ fetchOptions: { throw: true } }),
    },
  },
  passkeys: {
    getAll: {
      queryKey: [KEY, "passkeys"],
      queryFn: () =>
        authClient.passkey.listUserPasskeys({ fetchOptions: { throw: true } }),
    },
  },
};

const mutations = {
  signIn: {
    email: {
      mutationKey: [KEY, "signIn", "email"],
      mutationFn: (params: Parameters<typeof authClient.signIn.email>[0]) =>
        authClient.signIn.email(params),
    },
    magicLink: {
      mutationKey: [KEY, "signIn", "magicLink"],
      mutationFn: (params: Parameters<typeof authClient.signIn.magicLink>[0]) =>
        authClient.signIn.magicLink(params),
    },
    anonymous: {
      mutationKey: [KEY, "signIn", "anonymous"],
      mutationFn: (
        params?: Parameters<typeof authClient.signIn.anonymous>[0],
      ) => authClient.signIn.anonymous(params),
    },
    social: {
      mutationKey: [KEY, "signIn", "social"],
      mutationFn: (params: Parameters<typeof authClient.signIn.social>[0]) =>
        authClient.signIn.social(params),
    },
    passkey: {
      mutationKey: [KEY, "signIn", "passkey"],
      mutationFn: (params?: Parameters<typeof authClient.signIn.passkey>[0]) =>
        authClient.signIn.passkey(params),
    },
  },
  password: {
    forget: {
      mutationKey: [KEY, "password", "forget"],
      mutationFn: (
        params: Parameters<typeof authClient.requestPasswordReset>[0],
      ) => authClient.requestPasswordReset(params),
    },
    reset: {
      mutationKey: [KEY, "password", "update"],
      mutationFn: (params: Parameters<typeof authClient.resetPassword>[0]) =>
        authClient.resetPassword(params),
    },
    change: {
      mutationKey: [KEY, "password", "change"],
      mutationFn: (params: Parameters<typeof authClient.changePassword>[0]) =>
        authClient.changePassword(params),
    },
  },
  signOut: {
    mutationKey: [KEY, "signOut"],
    mutationFn: (params: Parameters<typeof authClient.signOut>[0]) =>
      authClient.signOut(params),
  },
  signUp: {
    email: {
      mutationKey: [KEY, "signUp", "email"],
      mutationFn: (params: Parameters<typeof authClient.signUp.email>[0]) =>
        authClient.signUp.email(params),
    },
  },
  twoFactor: {
    enable: {
      mutationKey: [KEY, "twoFactor", "enable"],
      mutationFn: (params: Parameters<typeof authClient.twoFactor.enable>[0]) =>
        authClient.twoFactor.enable({
          ...params,
          fetchOptions: { throw: true },
        }),
    },
    disable: {
      mutationKey: [KEY, "twoFactor", "disable"],
      mutationFn: (
        params: Parameters<typeof authClient.twoFactor.disable>[0],
      ) => authClient.twoFactor.disable(params),
    },
    backupCodes: {
      generate: {
        mutationKey: [KEY, "twoFactor", "backupCodes", "generate"],
        mutationFn: (
          params: Parameters<
            typeof authClient.twoFactor.generateBackupCodes
          >[0],
        ) =>
          authClient.twoFactor.generateBackupCodes({
            ...params,
            fetchOptions: {
              throw: true,
            },
          }),
      },
      verify: {
        mutationKey: [KEY, "twoFactor", "backupCodes", "verify"],
        mutationFn: (
          params: Parameters<typeof authClient.twoFactor.verifyBackupCode>[0],
        ) => authClient.twoFactor.verifyBackupCode(params),
      },
    },
    totp: {
      getUri: {
        mutationKey: [KEY, "twoFactor", "totp", "getUri"],
        mutationFn: (
          params: Parameters<typeof authClient.twoFactor.getTotpUri>[0],
        ) =>
          authClient.twoFactor.getTotpUri({
            ...params,
            fetchOptions: { throw: true },
          }),
      },
      verify: {
        mutationKey: [KEY, "twoFactor", "totp", "verify"],
        mutationFn: (
          params: Parameters<typeof authClient.twoFactor.verifyTotp>[0],
        ) => authClient.twoFactor.verifyTotp(params),
      },
    },
  },
  email: {
    sendVerification: {
      mutationKey: [KEY, "email", "sendVerification"],
      mutationFn: (
        params: Parameters<typeof authClient.sendVerificationEmail>[0],
      ) => authClient.sendVerificationEmail(params),
    },
    change: {
      mutationKey: [KEY, "email", "change"],
      mutationFn: (params: Parameters<typeof authClient.changeEmail>[0]) =>
        authClient.changeEmail(params),
    },
  },
  sessions: {
    revoke: {
      mutationKey: [KEY, "sessions", "revoke"],
      mutationFn: (token: string) => authClient.revokeSession({ token }),
    },
  },
  accounts: {
    connect: {
      mutationKey: [KEY, "accounts", "connect"],
      mutationFn: (params: Parameters<typeof authClient.linkSocial>[0]) =>
        authClient.linkSocial(params),
    },
    disconnect: {
      mutationKey: [KEY, "accounts", "disconnect"],
      mutationFn: (params: Parameters<typeof authClient.unlinkAccount>[0]) =>
        authClient.unlinkAccount(params),
    },
  },
  passkeys: {
    add: {
      mutationKey: [KEY, "passkeys", "add"],
      mutationFn: async () => {
        const response = await authClient.passkey.addPasskey();
        if (response.error) {
          throw new Error(response.error.message);
        }
        return response.data;
      },
    },
    delete: {
      mutationKey: [KEY, "passkeys", "delete"],
      mutationFn: async (
        params: Parameters<typeof authClient.passkey.deletePasskey>[0],
      ) => {
        const response = await authClient.passkey.deletePasskey(params);
        if (response.error) {
          throw new Error(response.error.message);
        }
        return response.data;
      },
    },
  },
};

export const auth = {
  queries,
  mutations,
};
