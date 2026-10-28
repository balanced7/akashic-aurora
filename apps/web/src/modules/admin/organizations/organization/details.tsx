"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { updateOrganizationSchema } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { useDebounceCallback } from "@akashic-labs/shared/hooks";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Input } from "@akashic-labs/ui-web/input";

import {
  DetailsList,
  DetailsListItem,
} from "~/modules/admin/layout/details-list";
import { admin } from "~/modules/admin/lib/api";

import type { UpdateOrganizationPayload } from "@akashic-labs/auth";

const Name = ({ id }: { id: string }) => {
  const { t } = useTranslation(["common", "admin"]);
  const queryClient = useQueryClient();
  const { data: organization } = useQuery(
    admin.queries.organizations.get({ id }),
  );

  const update = useMutation({
    ...admin.mutations.organizations.update,
    onSuccess: async () => {
      await queryClient.invalidateQueries(
        admin.queries.organizations.get({ id }),
      );
      toast.success(
        t("organizations.organization.details.name.update.success"),
      );
    },
  });

  const form = useForm({
    resolver: standardSchemaResolver(
      updateOrganizationSchema.pick({ name: true }),
    ),
    defaultValues: {
      name: organization?.name,
    },
  });

  const onSubmit = async (data: Pick<UpdateOrganizationPayload, "name">) => {
    await update.mutateAsync({ id, ...data });
  };

  const debouncedOnSubmit = useDebounceCallback(
    form.handleSubmit(onSubmit),
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

const Slug = ({ id }: { id: string }) => {
  const { t } = useTranslation(["common", "admin"]);
  const queryClient = useQueryClient();
  const { data: organization } = useQuery(
    admin.queries.organizations.get({ id }),
  );

  const update = useMutation({
    ...admin.mutations.organizations.update,
    onSuccess: async () => {
      await queryClient.invalidateQueries(
        admin.queries.organizations.get({ id }),
      );
      toast.success(
        t("organizations.organization.details.slug.update.success"),
      );
    },
  });

  const form = useForm({
    resolver: standardSchemaResolver(
      updateOrganizationSchema.pick({ slug: true }),
    ),
    defaultValues: {
      slug: organization?.slug ?? "",
    },
  });

  const onSubmit = async (data: Pick<UpdateOrganizationPayload, "slug">) => {
    await update.mutateAsync({ id, ...data });
  };

  const debouncedOnSubmit = useDebounceCallback(
    form.handleSubmit(onSubmit),
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
          name="slug"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center gap-1.5">
                <FormLabel>{t("slug")}</FormLabel>
                {form.formState.isSubmitting && (
                  <Icons.Loader2 className="size-3 animate-spin" />
                )}
              </div>
              <FormControl>
                <div className="relative">
                  <Input
                    className="peer ps-6"
                    {...field}
                    onChange={(e) => {
                      field.onChange(e.target.value);
                      void debouncedOnSubmit();
                    }}
                    disabled={form.formState.isSubmitting}
                  />
                  <div className="text-muted-foreground/80 pointer-events-none absolute inset-y-0 start-0 flex items-center justify-center ps-3 text-sm peer-disabled:opacity-50">
                    /
                  </div>
                </div>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  );
};

interface OrganizationDetailsProps {
  readonly id: string;
}

export const OrganizationDetails = ({ id }: OrganizationDetailsProps) => {
  const { t, i18n } = useTranslation(["common", "admin"]);
  const { data: organization } = useQuery(
    admin.queries.organizations.get({ id }),
  );

  const details = [
    {
      id: "name",
      component: <Name id={id} />,
      visible: true,
    },
    {
      id: "slug",
      component: <Slug id={id} />,
      visible: true,
    },
    {
      id: "createdAt",
      component: (
        <div className="flex flex-col items-start gap-3">
          <span className="text-sm font-medium">{t("createdAt")}</span>
          <span>{organization?.createdAt.toLocaleString(i18n.language)}</span>
        </div>
      ),
      visible: true,
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
