import * as z from "zod";

import { MemberRole, UserRole } from "../types";

const emailSchema = z.object({
  email: z.email().max(254),
});

const password = z.string().min(8);
const passwordSchema = z.object({
  password,
});

const otpSchema = z.object({
  code: z.string().min(6).max(6),
});

const backupCodeSchema = z.object({
  code: z.string().min(11).max(11),
});

const trustDeviceSchema = z.object({
  trustDevice: z.boolean().optional(),
});

const updateUserSchema = z.object({
  name: z.string().min(2).max(32).optional(),
  role: z.enum(UserRole).optional(),
  image: z.url().optional(),
});

const changePasswordSchema = z.object({
  ...passwordSchema.shape,
  newPassword: password,
});

const registerSchema = z.object({
  ...emailSchema.shape,
  ...passwordSchema.shape,
});

const passwordLoginSchema = z.object({
  ...emailSchema.shape,
  ...passwordSchema.shape,
  rememberMe: z.boolean().optional().default(true),
});

const magicLinkLoginSchema = emailSchema;
const forgotPasswordSchema = emailSchema;
const updatePasswordSchema = passwordSchema;

const otpVerificationSchema = z.object({
  ...otpSchema.shape,
  ...trustDeviceSchema.shape,
});

const backupCodeVerificationSchema = z.object({
  ...backupCodeSchema.shape,
  ...trustDeviceSchema.shape,
});

const createOrganizationSchema = z.object({
  name: z.string().min(2).max(32),
});

const updateOrganizationSchema = z.object({
  name: z.string().min(2).max(32).optional(),
  slug: z.string().optional(),
  logo: z.string().optional(),
});

const inviteMemberSchema = z.object({
  email: z.email().max(254),
  role: z.enum(MemberRole),
});

const updateMemberSchema = z.object({
  role: z.enum(MemberRole).optional(),
});

const banUserSchema = z.object({
  reason: z.string().min(1).max(1000).optional(),
  expiresIn: z
    .date()
    .optional()
    .refine((date) => !date || date > new Date()),
});

type EmailPayload = z.infer<typeof emailSchema>;
type PasswordLoginPayload = z.infer<typeof passwordLoginSchema>;
type MagicLinkLoginPayload = z.infer<typeof magicLinkLoginSchema>;
type RegisterPayload = z.infer<typeof registerSchema>;
type ForgotPasswordPayload = z.infer<typeof forgotPasswordSchema>;
type UpdatePasswordPayload = z.infer<typeof updatePasswordSchema>;
type PasswordPayload = z.infer<typeof passwordSchema>;
type UpdateUserPayload = z.infer<typeof updateUserSchema>;
type ChangePasswordPayload = z.infer<typeof changePasswordSchema>;
type OtpPayload = z.infer<typeof otpSchema>;
type OtpVerificationPayload = z.infer<typeof otpVerificationSchema>;
type BackupCodePayload = z.infer<typeof backupCodeSchema>;
type BackupCodeVerificationPayload = z.infer<
  typeof backupCodeVerificationSchema
>;
type CreateOrganizationPayload = z.infer<typeof createOrganizationSchema>;
type UpdateOrganizationPayload = z.infer<typeof updateOrganizationSchema>;
type InviteMemberPayload = z.infer<typeof inviteMemberSchema>;
type UpdateMemberPayload = z.infer<typeof updateMemberSchema>;
type BanUserPayload = z.infer<typeof banUserSchema>;

export {
  passwordSchema,
  registerSchema,
  passwordLoginSchema,
  magicLinkLoginSchema,
  forgotPasswordSchema,
  updatePasswordSchema,
  updateUserSchema,
  emailSchema,
  changePasswordSchema,
  otpSchema,
  otpVerificationSchema,
  backupCodeSchema,
  backupCodeVerificationSchema,
  createOrganizationSchema,
  updateOrganizationSchema,
  inviteMemberSchema,
  updateMemberSchema,
  banUserSchema,
};

export type {
  PasswordLoginPayload,
  MagicLinkLoginPayload,
  RegisterPayload,
  ForgotPasswordPayload,
  UpdatePasswordPayload,
  PasswordPayload,
  UpdateUserPayload,
  EmailPayload,
  ChangePasswordPayload,
  OtpPayload,
  OtpVerificationPayload,
  BackupCodePayload,
  BackupCodeVerificationPayload,
  CreateOrganizationPayload,
  UpdateOrganizationPayload,
  InviteMemberPayload,
  UpdateMemberPayload,
  BanUserPayload,
};
