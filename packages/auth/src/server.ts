import { expo } from "@better-auth/expo";
import { passkey } from "@better-auth/passkey";
import { drizzleAdapter } from "better-auth/adapters/drizzle";
import { betterAuth } from "better-auth/minimal";
import { nextCookies } from "better-auth/next-js";
import {
  anonymous,
  magicLink,
  twoFactor,
  organization,
  admin,
  lastLoginMethod,
} from "better-auth/plugins";

import * as schema from "@akashic-labs/db/schema";
import { db } from "@akashic-labs/db/server";
import { EmailTemplate } from "@akashic-labs/email";
import { sendEmail } from "@akashic-labs/email/server";
import { getLocaleFromRequest } from "@akashic-labs/i18n/server";
import { NodeEnv } from "@akashic-labs/shared/constants";

import { env } from "./env";
import { getUrl } from "./lib/utils";
import { AuthProvider, SocialProvider, VerificationType } from "./types";

export const auth = betterAuth({
  appName: "Akashic Labs",
  session: {
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60, // 5 minutes
    },
  },
  user: {
    deleteUser: {
      enabled: true,
      sendDeleteAccountVerification: async ({ user, url }, request) =>
        sendEmail({
          to: user.email,
          template: EmailTemplate.DELETE_ACCOUNT,
          locale: getLocaleFromRequest(request),
          variables: {
            url: getUrl({
              request,
              url,
              type: VerificationType.DELETE_ACCOUNT,
            }).toString(),
          },
        }),
    },
    changeEmail: {
      enabled: true,
      updateEmailWithoutVerification: true,
      sendChangeEmailConfirmation: async ({ user, newEmail, url }, request) =>
        sendEmail({
          to: user.email,
          template: EmailTemplate.CHANGE_EMAIL,
          locale: getLocaleFromRequest(request),
          variables: {
            url: getUrl({
              request,
              url,
              type: VerificationType.CONFIRM_EMAIL,
            }).toString(),
            newEmail,
          },
        }),
    },
  },
  trustedOrigins: [
    "chrome-extension://",
    "akashic-labs://",
    /* Needed only for Apple ID authentication */
    "https://appleid.apple.com",
    ...(env.NODE_ENV === NodeEnv.DEVELOPMENT
      ? ["http://localhost*", "https://localhost*"]
      : []),
  ],
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: true,
    sendResetPassword: async ({ user, url }, request) =>
      sendEmail({
        to: user.email,
        template: EmailTemplate.RESET_PASSWORD,
        locale: getLocaleFromRequest(request),
        variables: {
          url,
        },
      }),
  },
  emailVerification: {
    sendOnSignUp: true,
    autoSignInAfterVerification: true,
    sendVerificationEmail: async ({ user, url }, request) =>
      sendEmail({
        to: user.email,
        template: EmailTemplate.CONFIRM_EMAIL,
        locale: getLocaleFromRequest(request),
        variables: {
          url: getUrl({
            request,
            url,
            type: VerificationType.CONFIRM_EMAIL,
          }).toString(),
        },
      }),
  },
  database: drizzleAdapter(db, {
    provider: "pg",
    schema,
  }),
  plugins: [
    magicLink({
      sendMagicLink: async ({ email, url }, ctx) =>
        sendEmail({
          to: email,
          template: EmailTemplate.MAGIC_LINK,
          locale: getLocaleFromRequest(ctx?.request),
          variables: {
            url: getUrl({
              request: ctx?.request,
              url,
              type: VerificationType.MAGIC_LINK,
            }).toString(),
          },
        }),
    }),
    passkey(),
    twoFactor(),
    anonymous(),
    admin(),
    organization({
      sendInvitationEmail: async (
        { invitation, inviter, organization },
        request,
      ) => {
        const url = getUrl({
          request,
        });
        url.searchParams.set("invitationId", invitation.id);
        url.searchParams.set("email", invitation.email);

        return sendEmail({
          to: invitation.email,
          template: EmailTemplate.ORGANIZATION_INVITATION,
          locale: getLocaleFromRequest(request),
          variables: {
            url: url.toString(),
            inviter: inviter.user.name,
            organization: organization.name,
          },
        });
      },
    }),
    lastLoginMethod({
      customResolveMethod: (ctx) => {
        switch (ctx.path) {
          case "/magic-link/verify":
            return AuthProvider.MAGIC_LINK;
          case "/passkey/verify-authentication":
            return AuthProvider.PASSKEY;
          default:
            return null;
        }
      },
    }),
    expo(),
    nextCookies(),
  ],
  socialProviders: {
    [SocialProvider.APPLE]: {
      clientId: env.APPLE_CLIENT_ID,
      clientSecret: env.APPLE_CLIENT_SECRET,
      appBundleIdentifier: env.APPLE_APP_BUNDLE_IDENTIFIER,
    },
    [SocialProvider.GOOGLE]: {
      clientId: env.GOOGLE_CLIENT_ID,
      clientSecret: env.GOOGLE_CLIENT_SECRET,
    },
    [SocialProvider.GITHUB]: {
      clientId: env.GITHUB_CLIENT_ID,
      clientSecret: env.GITHUB_CLIENT_SECRET,
    },
  },
  advanced: {
    cookiePrefix: "akashic-labs",
    cookies: {
      state: {
        attributes: {
          sameSite: "none",
          secure: true,
        },
      },
    },
  },
});

export type AuthErrorCode = keyof typeof auth.$ERROR_CODES;
export type Session = typeof auth.$Infer.Session;
export type User = Session["user"];
export type Invitation = typeof auth.$Infer.Invitation;
export type Organization = typeof auth.$Infer.Organization;
export type ActiveOrganization = typeof auth.$Infer.ActiveOrganization;
export type Member = typeof auth.$Infer.Member;
