"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { memo } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { updateUserSchema } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Input } from "@akashic-labs/ui-web/input";

import {
  SettingsCard,
  SettingsCardContent,
  SettingsCardDescription,
  SettingsCardFooter,
  SettingsCardHeader,
  SettingsCardTitle,
} from "~/modules/common/layout/dashboard/settings-card";
import { onPromise } from "~/utils";

import { user } from "../../lib/api";

import type { User } from "@akashic-labs/auth";

interface EditNameProps {
  readonly user: User;
}

export const EditName = memo<EditNameProps>((props) => {
  const { t } = useTranslation(["common", "auth"]);
  const router = useRouter();
  const form = useForm({
    resolver: standardSchemaResolver(updateUserSchema.pick({ name: true })),
    defaultValues: {
      name: props.user.name,
    },
  });

  const updateUser = useMutation({
    ...user.mutations.update,
    onSuccess: () => {
      toast.success(t("account.name.edit.success"));
      router.refresh();
    },
  });

  return (
    <SettingsCard>
      <SettingsCardHeader>
        <SettingsCardTitle>{t("name")}</SettingsCardTitle>
        <SettingsCardDescription>
          {t("account.name.edit.description")}
        </SettingsCardDescription>
      </SettingsCardHeader>

      <Form {...form}>
        <form
          onSubmit={onPromise(
            form.handleSubmit((data) => updateUser.mutateAsync(data)),
          )}
        >
          <SettingsCardContent>
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Input
                      {...field}
                      type="text"
                      disabled={form.formState.isSubmitting}
                      className="max-w-xs"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </SettingsCardContent>

          <SettingsCardFooter>
            {t("account.name.edit.info")}
            <Button size="sm" disabled={form.formState.isSubmitting}>
              {form.formState.isSubmitting ? (
                <Icons.Loader2 className="size-4 animate-spin" />
              ) : (
                t("save")
              )}
            </Button>
          </SettingsCardFooter>
        </form>
      </Form>
    </SettingsCard>
  );
});

EditName.displayName = "EditName";
