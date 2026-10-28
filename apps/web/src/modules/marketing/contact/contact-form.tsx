"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { useTranslation } from "@akashic-labs/i18n";
import { Button } from "@akashic-labs/ui-web/button";
import { Card, CardContent } from "@akashic-labs/ui-web/card";
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
import { Textarea } from "@akashic-labs/ui-web/textarea";

import { sendContactForm } from "./actions";
import { contactFormSchema, MAX_MESSAGE_LENGTH } from "./utils/schema";

import type { ContactFormPayload } from "./utils/schema";

export function ContactForm() {
  const { t } = useTranslation(["common", "marketing"]);
  const form = useForm({
    resolver: standardSchemaResolver(contactFormSchema),
    defaultValues: {
      name: "",
      email: "",
      message: "",
    },
  });

  const message = form.watch("message");

  const onSubmit = async (data: ContactFormPayload) => {
    const { error } = await sendContactForm(data);

    if (error) {
      return toast.error(error);
    }

    toast.success(t("contact.form.success.title"), {
      description: t("contact.form.success.description"),
    });

    form.reset();
  };

  return (
    <Card className="w-full max-w-lg border-none shadow-none">
      <CardContent className="w-full p-0">
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-col gap-4"
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("name")}</FormLabel>
                  <FormControl>
                    <Input
                      placeholder={t("contact.form.name.placeholder")}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("email")}</FormLabel>
                  <FormControl>
                    <Input
                      placeholder={t("contact.form.email.placeholder")}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="message"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="mt-2 flex justify-between">
                    <span>{t("message")}</span>
                    <span className="text-muted-foreground text-xs">
                      {message.length}/{MAX_MESSAGE_LENGTH}
                    </span>
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={t("contact.form.message.placeholder")}
                      className="min-h-[120px]"
                      maxLength={MAX_MESSAGE_LENGTH}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button
              type="submit"
              className="mt-2"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? (
                <Icons.Loader2 className="size-5 animate-spin" />
              ) : (
                t("contact.form.submit")
              )}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
