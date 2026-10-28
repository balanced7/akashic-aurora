"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { updateUserSchema, UserRole } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { useDebounceCallback } from "@akashic-labs/shared/hooks";
import {
  Form,
  FormField,
  FormItem,
  FormControl,
  FormLabel,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Input } from "@akashic-labs/ui-web/input";
import {
  Select,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectPortal,
} from "@akashic-labs/ui-web/select";

import {
  DetailsList,
  DetailsListItem,
} from "~/modules/admin/layout/details-list";
import { admin } from "~/modules/admin/lib/api";

const Role = ({ id }: { id: string }) => {
  const { t } = useTranslation(["common", "admin"]);

  const queryClient = useQueryClient();
  const { data: user } = useQuery(admin.queries.users.get({ id }));

  const form = useForm({
    resolver: standardSchemaResolver(updateUserSchema.pick({ role: true })),
    defaultValues: {
      role: user?.role as UserRole,
    },
  });

  const updateUser = useMutation({
    ...admin.mutations.users.update,
    onSuccess: async () => {
      await queryClient.invalidateQueries(admin.queries.users.get({ id }));
      toast.success(t("users.user.details.role.update.success"));
    },
  });

  return (
    <Form {...form}>
      <form>
        <FormField
          control={form.control}
          name="role"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center gap-1.5">
                <FormLabel>{t("role")}</FormLabel>
                {form.formState.isSubmitting && (
                  <Icons.Loader2 className="size-3 animate-spin" />
                )}
              </div>
              <FormControl>
                <div>
                  <Select
                    value={field.value}
                    onValueChange={(value) => {
                      field.onChange(value);
                      void form.handleSubmit((data) =>
                        updateUser.mutateAsync({
                          data,
                          userId: id,
                        }),
                      )();
                    }}
                    disabled={form.formState.isSubmitting}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder={t("role")} />
                    </SelectTrigger>
                    <SelectPortal>
                      <SelectContent>
                        {Object.values(UserRole).map((role) => (
                          <SelectItem key={role} value={role}>
                            {t(role)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </SelectPortal>
                  </Select>
                </div>
              </FormControl>
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
};

const Name = ({ id }: { id: string }) => {
  const { t } = useTranslation(["common", "admin"]);
  const queryClient = useQueryClient();
  const { data: user } = useQuery(admin.queries.users.get({ id }));

  const form = useForm({
    resolver: standardSchemaResolver(updateUserSchema.pick({ name: true })),
    defaultValues: {
      name: user?.name,
    },
  });

  const updateUser = useMutation({
    ...admin.mutations.users.update,
    onSuccess: async () => {
      await queryClient.invalidateQueries(admin.queries.users.get({ id }));
      toast.success(t("users.user.details.name.update.success"));
    },
  });

  const debouncedOnSubmit = useDebounceCallback(
    form.handleSubmit((data) =>
      updateUser.mutateAsync({
        data,
        userId: id,
      }),
    ),
    2000,
    {
      trailing: true,
      leading: false,
    },
  );

  return (
    <Form {...form}>
      <form>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center gap-1.5">
                <FormLabel>{t("name")}</FormLabel>
                {form.formState.isSubmitting && (
                  <Icons.Loader2 className="size-3 animate-spin" />
                )}
              </div>
              <FormControl>
                <Input
                  {...field}
                  onChange={(e) => {
                    field.onChange(e.target.value);
                    void debouncedOnSubmit();
                  }}
                  disabled={form.formState.isSubmitting}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
};

interface UserDetailsProps {
  readonly id: string;
}

export const UserDetails = ({ id }: UserDetailsProps) => {
  const { t, i18n } = useTranslation(["common", "auth"]);
  const { data: user } = useQuery(admin.queries.users.get({ id }));

  const details = [
    {
      id: "name",
      component: <Name id={id} />,
      visible: true,
    },
    {
      id: "role",
      component: <Role id={id} />,
      visible: true,
    },
    {
      id: "twoFactorEnabled",
      component: (
        <div className="flex flex-col items-start gap-3">
          <span className="text-sm font-medium">{t("two-factor")}</span>
          <span>{user?.twoFactorEnabled ? t("enabled") : t("disabled")}</span>
        </div>
      ),
      visible: true,
    },
    {
      id: "createdAt",
      component: (
        <div className="flex flex-col items-start gap-3">
          <span className="text-sm font-medium">{t("createdAt")}</span>
          <span>{user?.createdAt.toLocaleString(i18n.language)}</span>
        </div>
      ),
      visible: true,
    },
    {
      id: "updatedAt",
      component: (
        <div className="flex flex-col items-start gap-3">
          <span className="text-sm font-medium">{t("updatedAt")}</span>
          <span>{user?.updatedAt.toLocaleString(i18n.language)}</span>
        </div>
      ),
      visible: true,
    },
    {
      id: "banExpires",
      component: (
        <div className="flex flex-col items-start gap-3">
          <span className="text-sm font-medium">{t("banExpiresIn")}</span>
          {user?.banExpires ? (
            <span>{user.banExpires.toLocaleString(i18n.language)}</span>
          ) : (
            <span>{t("never")}</span>
          )}
        </div>
      ),
      visible: !!user?.banned,
    },
    {
      id: "banReason",
      component: (
        <div className="flex flex-col items-start gap-3">
          <span className="text-sm font-medium">{t("banReason")}</span>
          <p>{user?.banReason}</p>
        </div>
      ),
      visible: !!user?.banned,
    },
  ];

  return (
    <section className="@container/details w-full overflow-hidden">
      <DetailsList>
        {details
          .filter((detail) => detail.visible)
          .map((detail) => (
            <DetailsListItem key={detail.id}>
              {detail.component}
            </DetailsListItem>
          ))}
      </DetailsList>
    </section>
  );
};
