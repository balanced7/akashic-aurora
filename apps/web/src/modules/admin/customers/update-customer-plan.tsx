"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { updateCustomerInputSchema } from "@akashic-labs/api/schema";
import { BillingStatus, config } from "@akashic-labs/billing";
import { isKey, useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Form,
  FormControl,
  FormField,
  FormDescription,
  FormItem,
  FormLabel,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import {
  Modal,
  ModalClose,
  ModalContent,
  ModalDescription,
  ModalFooter,
  ModalHeader,
  ModalTitle,
  ModalTrigger,
} from "@akashic-labs/ui-web/modal";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@akashic-labs/ui-web/select";

import { admin } from "~/modules/admin/lib/api";

import { invalidateCustomers } from "./server/invalidate";

import type { UpdateCustomerInput } from "@akashic-labs/api/schema";
import type { User } from "@akashic-labs/auth";
import type { Customer } from "@akashic-labs/billing";
import type { UseFormReturn } from "react-hook-form";

interface UpdateCustomerPlanModalProps {
  readonly customer: Customer & { user: Pick<User, "name"> };
  readonly children: React.ReactNode;
}
const UpdateCustomerPlanForm = ({
  form,
  onSubmit,
}: {
  form: UseFormReturn<Pick<UpdateCustomerInput, "plan" | "status">>;
  onSubmit: (
    data: Pick<UpdateCustomerInput, "plan" | "status">,
  ) => void | Promise<void>;
}) => {
  const { t, i18n } = useTranslation(["common", "admin", "billing"]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="plan"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("common:plan")}</FormLabel>
              <FormControl>
                <div>
                  <Select
                    value={field.value ?? undefined}
                    onValueChange={field.onChange}
                    disabled={form.formState.isSubmitting}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder={t("common:plan")} />
                    </SelectTrigger>
                    <SelectContent>
                      {config.plans.map((plan) => (
                        <SelectItem key={plan.id} value={plan.id}>
                          {isKey(plan.name, i18n, "billing")
                            ? t(plan.name)
                            : plan.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </FormControl>
              <FormDescription>
                {t("customers.customer.updatePlan.plan.info")}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="status"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("common:status")}</FormLabel>
              <FormControl>
                <div>
                  <Select
                    value={field.value ?? undefined}
                    onValueChange={field.onChange}
                    disabled={form.formState.isSubmitting}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder={t("common:status")} />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.values(BillingStatus).map((status) => {
                        const statusKey = `status.${status
                          .toLowerCase()
                          .replace(/_([a-z])/g, (_, letter: string) =>
                            letter.toUpperCase(),
                          )}`;
                        return (
                          <SelectItem key={status} value={status}>
                            {isKey(statusKey, i18n, "billing")
                              ? t(statusKey)
                              : statusKey}
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                </div>
              </FormControl>
              <FormDescription>
                {t("customers.customer.updatePlan.status.info")}
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
  );
};

export const UpdateCustomerPlanModal = ({
  customer,
  children,
}: UpdateCustomerPlanModalProps) => {
  const { t } = useTranslation(["common", "admin", "billing"]);
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const form = useForm({
    resolver: standardSchemaResolver(
      updateCustomerInputSchema.pick({ plan: true, status: true }),
    ),
    defaultValues: {
      plan: customer.plan ?? undefined,
      status: customer.status ?? undefined,
    },
  });

  const updateCustomer = useMutation({
    ...admin.mutations.customers.update,
    onSuccess: async () => {
      await invalidateCustomers();
      await queryClient.invalidateQueries(
        admin.queries.users.getPlans({
          id: customer.userId,
        }),
      );
      toast.success(t("customers.customer.updatePlan.success"));
      setOpen(false);
      form.reset();
    },
  });

  const onSubmit = async (
    data: Pick<UpdateCustomerInput, "plan" | "status">,
  ) => {
    await updateCustomer.mutateAsync({ id: customer.id, ...data });
  };

  return (
    <Modal open={open} onOpenChange={setOpen}>
      <ModalTrigger asChild>{children}</ModalTrigger>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>
            {t("customers.customer.updatePlan.title", {
              name: customer.user.name,
            })}
          </ModalTitle>
          <ModalDescription>
            {t("customers.customer.updatePlan.description")}
          </ModalDescription>
        </ModalHeader>

        <UpdateCustomerPlanForm form={form} onSubmit={onSubmit} />
      </ModalContent>
    </Modal>
  );
};
