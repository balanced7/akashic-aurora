"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import {
  getAllRolesAtOrBelow,
  MemberRole,
  updateMemberSchema,
} from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import {
  Modal,
  ModalTrigger,
  ModalTitle,
  ModalHeader,
  ModalContent,
  ModalDescription,
  ModalClose,
  ModalFooter,
} from "@akashic-labs/ui-web/modal";
import {
  Select,
  SelectItem,
  SelectValue,
  SelectContent,
  SelectTrigger,
} from "@akashic-labs/ui-web/select";

import { organization } from "~/modules/organization/lib/api";

import { useActiveOrganization } from "../hooks/use-active-organization";

import type { Member } from "@akashic-labs/auth";

interface UpdateMemberRoleModalProps {
  readonly member: Member;
  readonly children: React.ReactNode;
}

export const UpdateMemberRoleModal = ({
  member,
  children,
}: UpdateMemberRoleModalProps) => {
  const { t } = useTranslation(["common", "organization"]);
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const { activeMember } = useActiveOrganization();

  const form = useForm({
    resolver: standardSchemaResolver(updateMemberSchema.pick({ role: true })),
    defaultValues: {
      role: member.role,
    },
  });

  const updateMemberRole = useMutation({
    ...organization.mutations.members.updateRole,
    onSuccess: async () => {
      await queryClient.invalidateQueries(
        organization.queries.members.getAll({ id: member.organizationId }),
      );
      toast.success(t("members.update.role.success"));
      setOpen(false);
      form.reset();
    },
  });

  return (
    <Modal open={open} onOpenChange={setOpen}>
      <ModalTrigger asChild>{children}</ModalTrigger>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>
            {t("members.update.role.title", {
              name: member.user.name,
            })}
          </ModalTitle>
          <ModalDescription>
            {t("members.update.role.description")}
          </ModalDescription>
        </ModalHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit((data) =>
              updateMemberRole.mutateAsync({
                memberId: member.id,
                role: data.role ?? MemberRole.MEMBER,
              }),
            )}
            className="space-y-6"
          >
            <FormField
              control={form.control}
              name="role"
              render={({ field }) => (
                <FormItem className="px-4 md:px-0">
                  <FormLabel>{t("role")}</FormLabel>
                  <FormControl>
                    <div>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                        disabled={form.formState.isSubmitting}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder={t("role")} />
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
                  <FormDescription>
                    {t("members.update.role.info")}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <ModalFooter>
              <ModalClose asChild>
                <Button variant="outline" type="button">
                  {t("cancel")}
                </Button>
              </ModalClose>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? (
                  <Icons.Loader2 className="animate-spin" />
                ) : (
                  t("update")
                )}
              </Button>
            </ModalFooter>
          </form>
        </Form>
      </ModalContent>
    </Modal>
  );
};
