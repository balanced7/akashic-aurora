"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm } from "react-hook-form";
import { toast } from "sonner";
import * as z from "zod";

import {
  getAllRolesAtOrBelow,
  inviteMemberSchema,
  MemberRole,
} from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Input } from "@akashic-labs/ui-web/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@akashic-labs/ui-web/select";

import { authClient } from "~/lib/auth/client";
import {
  SettingsCard,
  SettingsCardDescription,
  SettingsCardContent,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";
import { useActiveOrganization } from "~/modules/organization/hooks/use-active-organization";
import { organization } from "~/modules/organization/lib/api";

interface InviteMemberProps {
  organizationId: string;
}

export const InviteMember = ({ organizationId }: InviteMemberProps) => {
  const { t } = useTranslation(["common", "organization"]);
  const queryClient = useQueryClient();
  const { activeMember } = useActiveOrganization();

  const schema = z.object({
    invites: z.array(inviteMemberSchema).min(1),
  });

  const form = useForm({
    resolver: standardSchemaResolver(schema),
    defaultValues: {
      invites: [{ email: "", role: MemberRole.MEMBER }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "invites",
  });

  const inviteMember = useMutation(organization.mutations.members.invite);

  const onSubmit = async (data: z.infer<typeof schema>) => {
    const results = await Promise.allSettled(
      data.invites.map((invite) =>
        inviteMember.mutateAsync({ ...invite, organizationId }),
      ),
    );

    const failedInvites = results
      .map((result, idx) =>
        result.status === "rejected" ? data.invites[idx] : null,
      )
      .filter(Boolean);

    const successCount = data.invites.length - failedInvites.length;
    if (successCount > 0) {
      toast.success(t("members.invite.success", { count: successCount }));
    }

    if (failedInvites.length > 0) {
      form.reset({ invites: failedInvites });
    } else {
      form.reset(undefined, { keepDefaultValues: true });
    }

    await queryClient.invalidateQueries(
      organization.queries.invitations.getAll({ id: organizationId }),
    );
  };

  const hasInvitePermission = authClient.organization.checkRolePermission({
    permission: {
      invitation: ["create"],
    },
    role: activeMember?.role ?? MemberRole.MEMBER,
  });

  return (
    <SettingsCard disabled={!hasInvitePermission}>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("members.invite.title")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("members.invite.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="mt-2">
          <SettingsCardContent className="flex w-full flex-col gap-2">
            {fields.map((field, index) => (
              <div key={field.id} className="flex w-full gap-2">
                <FormField
                  control={form.control}
                  name={`invites.${index}.email`}
                  render={({ field }) => (
                    <FormItem className="w-full">
                      <FormLabel className={cn({ "sr-only": index > 0 })}>
                        {t("email")}
                      </FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          type="email"
                          placeholder="jane@example.com"
                          disabled={
                            !hasInvitePermission || form.formState.isSubmitting
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name={`invites.${index}.role`}
                  render={({ field }) => (
                    <FormItem className="w-full">
                      <FormLabel className={cn({ "sr-only": index > 0 })}>
                        {t("role")}
                      </FormLabel>
                      <FormControl>
                        <div>
                          <Select
                            onValueChange={field.onChange}
                            value={field.value}
                            disabled={
                              !hasInvitePermission ||
                              form.formState.isSubmitting
                            }
                          >
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder={t("member")} />
                            </SelectTrigger>
                            <SelectContent>
                              {getAllRolesAtOrBelow(
                                activeMember?.role ?? MemberRole.MEMBER,
                              ).map((role) => (
                                <SelectItem key={role} value={role}>
                                  {t(role)}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {fields.length > 1 && (
                  <div
                    className={cn({
                      "translate-y-[1.35rem]": !index,
                    })}
                  >
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      className="gap-2"
                      disabled={
                        !hasInvitePermission || form.formState.isSubmitting
                      }
                      onClick={() => remove(index)}
                    >
                      <Icons.Trash className="size-4" />
                      <span className="sr-only"> {t("remove")}</span>
                    </Button>
                  </div>
                )}
              </div>
            ))}

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append({ email: "", role: MemberRole.MEMBER })}
              className="mt-2 w-fit gap-2"
              disabled={!hasInvitePermission || form.formState.isSubmitting}
            >
              <Icons.Plus className="size-4" /> {t("addMore")}
            </Button>
          </SettingsCardContent>

          <SettingsCardFooter>
            {hasInvitePermission ? (
              <>
                {t("members.invite.info")}
                <Button disabled={form.formState.isSubmitting} size="sm">
                  {form.formState.isSubmitting ? (
                    <Icons.Loader2 className="size-4 animate-spin" />
                  ) : (
                    t("invite")
                  )}
                </Button>
              </>
            ) : (
              t("members.invite.missingPermission")
            )}
          </SettingsCardFooter>
        </form>
      </Form>
    </SettingsCard>
  );
};
