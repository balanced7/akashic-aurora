import { AuthProvider } from "@akashic-labs/auth";

export const LOGIN_OPTIONS = [AuthProvider.PASSWORD, AuthProvider.MAGIC_LINK];

export type LoginOption = (typeof LOGIN_OPTIONS)[number];
