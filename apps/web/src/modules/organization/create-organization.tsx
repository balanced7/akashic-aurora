import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { createOrganizationSchema } from "@akashic-labs/auth";
import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import {
  Form,
  FormControl,
  FormLabel,
  FormItem,
  FormField,
  FormDescription,
  FormMessage,
} from "@akashic-labs/ui-web/form";
import { Icons } from "@akashic-labs/ui-web/icons";
import { Input } from "@akashic-labs/ui-web/input";
import {
  Modal,
  ModalFooter,
  ModalContent,
  ModalHeader,
  ModalDescription,
  ModalTitle,
  ModalClose,
  ModalTrigger,
} from "@akashic-labs/ui-web/modal";

import { pathsConfig } from "~/config/paths";

import { organization } from "./lib/api";

import type { CreateOrganizationPayload } from "@akashic-labs/auth";

export const CreateOrganizationModal = ({
  open,
  onOpenChange,
  children,
}: {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children?: React.ReactNode;
}) => {
  const { t } = useTranslation(["common", "organization"]);
  const router = useRouter();

  const form = useForm({
    resolver: standardSchemaResolver(createOrganizationSchema),
    defaultValues: {
      name: "",
    },
  });

  const getSlug = useMutation(organization.mutations.getSlug);
  const create = useMutation({
    ...organization.mutations.create,
    onSuccess: (_, variables) => {
      router.replace(pathsConfig.dashboard.organization(variables.slug).index);
    },
  });

  const createOrganization = async (data: CreateOrganizationPayload) => {
    const { slug } = await getSlug.mutateAsync({
      query: data,
    });

    await create.mutateAsync({
      ...data,
      slug,
    });
  };

  return (
    <Modal open={open} onOpenChange={onOpenChange}>
      {children && <ModalTrigger asChild>{children}</ModalTrigger>}
      <ModalContent>
        <ModalHeader>
          <ModalTitle>{t("create.title")}</ModalTitle>
          <ModalDescription className="whitespace-pre-line">
            {t("create.description")}
          </ModalDescription>
        </ModalHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(createOrganization)}
            className="md:space-y-6"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem className="px-4 py-2 md:px-0 md:py-0">
                  <FormLabel>{t("common:name")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormDescription>{t("create.info")}</FormDescription>
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
                  t("create.cta")
                )}
              </Button>
            </ModalFooter>
          </form>
        </Form>
      </ModalContent>
    </Modal>
  );
};
