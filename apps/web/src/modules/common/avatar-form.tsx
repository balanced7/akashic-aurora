"use client";

import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useMutationState } from "@tanstack/react-query";
import { createContext, useContext, useState } from "react";
import { FormProvider, useForm, useFormContext } from "react-hook-form";
import { toast } from "sonner";
import * as z from "zod";

import { handle } from "@akashic-labs/api/utils";
import { useTranslation } from "@akashic-labs/i18n";
import { cn } from "@akashic-labs/ui";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@akashic-labs/ui-web/avatar";
import { Button } from "@akashic-labs/ui-web/button";
import { Icons } from "@akashic-labs/ui-web/icons";

import { api } from "~/lib/api/client";

interface AvatarFormProps {
  readonly id: string;
  readonly image?: string | null;
  readonly update: (
    image: string | null,
  ) => Promise<{ error: { message?: string } | null }>;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ACCEPTED_IMAGE_TYPES = [
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp",
];

const mutations = {
  upload: {
    mutationKey: ["avatar", "upload"],
    mutationFn: async ({
      avatar,
      id,
      image,
      update,
    }: AvatarFormProps & { avatar?: File }) => {
      const extension = avatar?.type.split("/").pop();
      const uuid = crypto.randomUUID();
      const path = `avatars/${id}-${uuid}.${extension}`;

      const { url: uploadUrl } = await handle(api.storage.upload.$get)({
        query: { path },
      });

      const response = await fetch(uploadUrl, {
        method: "PUT",
        body: avatar,
        headers: {
          "Content-Type": avatar?.type ?? "",
        },
      });

      if (!response.ok) {
        throw new Error();
      }

      const { url: publicUrl } = await handle(api.storage.public.$get)({
        query: { path },
      });

      const { error } = await update(publicUrl);

      if (error) {
        throw new Error(error.message);
      }

      return { publicUrl, oldImage: image };
    },
  },
  remove: {
    mutationKey: ["avatar", "remove"],
    mutationFn: async ({ image, update }: Omit<AvatarFormProps, "id">) => {
      const path = image?.split("/").pop();
      if (!path) {
        return;
      }

      const { url: deleteUrl } = await handle(api.storage.delete.$get)({
        query: { path: `avatars/${path}` },
      });

      const { error } = await update(null);

      if (error) {
        throw new Error(error.message);
      }

      void fetch(deleteUrl, {
        method: "DELETE",
      });
    },
  },
};

const useAvatarFormSchema = () => {
  const { t, i18n } = useTranslation("validation");

  return z.object({
    avatar: z
      .custom<FileList>()
      .refine(
        (files) => files.length === 1,
        t("error.file.maxCount", { count: 1 }),
      )
      .transform((files) => files[0])
      .refine(
        (file) => (file?.size ?? 0) <= MAX_FILE_SIZE,
        t("error.tooBig.file.inclusive", {
          maximum: MAX_FILE_SIZE,
        }),
      )
      .refine(
        (file) => ACCEPTED_IMAGE_TYPES.includes(file?.type ?? ""),
        t("error.file.type", {
          types: new Intl.ListFormat(i18n.language, {
            style: "long",
            type: "conjunction",
          }).format(ACCEPTED_IMAGE_TYPES.map((t) => t.replace("image/", "."))),
        }),
      ),
  });
};

interface AvatarFormContextValue extends AvatarFormProps {
  previewUrl: string | null;
  setPreviewUrl: (previewUrl: string | null) => void;
}

const AvatarFormContext = createContext<AvatarFormContextValue | null>(null);

const useAvatarFormContext = () => {
  const context = useContext(AvatarFormContext);
  if (!context) {
    throw new Error("useAvatarFormContext must be used within a AvatarForm!");
  }
  return context;
};

const AvatarForm = ({
  id,
  image,

  update,
  children,
}: AvatarFormProps & {
  children: React.ReactNode;
}) => {
  const [previewUrl, setPreviewUrl] = useState(image ?? null);
  const avatarSchema = useAvatarFormSchema();

  const form = useForm({
    resolver: standardSchemaResolver(avatarSchema),
  });

  return (
    <AvatarFormContext.Provider
      value={{ id, image, update, previewUrl, setPreviewUrl }}
    >
      <FormProvider {...form}>{children}</FormProvider>
    </AvatarFormContext.Provider>
  );
};

const AvatarFormInput = ({
  className,
  children,
  onUpload,
  disabled,
  ...props
}: React.ComponentProps<"input"> & { onUpload?: () => void }) => {
  const { t } = useTranslation("common");
  const { image, setPreviewUrl, id, update } = useAvatarFormContext();
  const avatarSchema = useAvatarFormSchema();

  const { register, handleSubmit, reset } =
    useFormContext<z.infer<typeof avatarSchema>>();

  const upload = useMutation({
    ...mutations.upload,
    onError: (error) => {
      setPreviewUrl(image ?? null);
      toast.error(error.message || t("error.general"));
    },
    onSuccess: async ({ publicUrl, oldImage }) => {
      await new Promise((resolve) => {
        const img = new Image();
        img.src = publicUrl;
        img.onload = resolve;
      });

      if (oldImage) {
        const oldPath = oldImage.split("/").pop();
        if (oldPath) {
          const { url: deleteUrl } = await handle(api.storage.delete.$get)({
            query: { path: `avatars/${oldPath}` },
          });
          void fetch(deleteUrl, { method: "DELETE" });
        }
      }

      onUpload?.();
    },
  });

  const [removeStatus] = useMutationState({
    filters: { mutationKey: mutations.remove.mutationKey },
    select: (mutation) => mutation.state.status,
  });

  const onSubmit = (data: z.infer<typeof avatarSchema>) => {
    upload.mutate({
      ...data,
      id,
      image,
      update,
    });
    reset();
  };

  return (
    <label
      className={cn(
        "group",
        {
          "cursor-pointer": !disabled,
          "cursor-not-allowed opacity-50": disabled,
        },
        className,
      )}
    >
      {children}
      <input
        {...register("avatar", {
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
            const file = e.target.files?.[0];

            if (!file) {
              return;
            }

            const isValid = avatarSchema.safeParse({
              avatar: e.target.files,
            });

            if (isValid.success) {
              const url = URL.createObjectURL(file);
              setPreviewUrl(url);
            }

            void handleSubmit(onSubmit)();
          },
        })}
        type="file"
        accept={ACCEPTED_IMAGE_TYPES.join(",")}
        className="sr-only"
        aria-label={t("update")}
        onClick={(e) => "value" in e.target && (e.target.value = "")}
        disabled={disabled ?? (upload.isPending || removeStatus === "pending")}
        {...props}
      />
    </label>
  );
};

const AvatarFormPreview = ({
  className,
  fallback,
  ...props
}: React.ComponentProps<typeof Avatar> & { fallback?: React.ReactNode }) => {
  const { previewUrl } = useAvatarFormContext();
  const { formState } = useFormContext();

  const mutationStatues = useMutationState({
    filters: {
      predicate: (mutation) =>
        [mutations.upload.mutationKey, mutations.remove.mutationKey].includes(
          mutation.options.mutationKey as string[],
        ),
    },
    select: (mutation) => mutation.state.status,
  });

  const hasError =
    formState.errors.avatar ??
    mutationStatues.some((status) => status === "error");

  return (
    <Avatar
      className={cn(
        `relative size-20 transition-all ${
          hasError
            ? "ring-destructive ring-offset-background ring-2 ring-offset-2"
            : "group-focus-within:ring-primary group-focus-within:ring-offset-background group-focus-within:ring-2 group-focus-within:ring-offset-2"
        }`,
        className,
      )}
      {...props}
    >
      {previewUrl && <AvatarImage src={previewUrl} />}
      {mutationStatues.some((status) => status === "pending") && (
        <div className="bg-background/60 absolute inset-0 flex items-center justify-center rounded-full backdrop-blur-sm">
          <Icons.Loader2 className="text-muted-foreground size-7 animate-spin" />
        </div>
      )}
      <AvatarFallback>
        {fallback ?? <Icons.UserRound className="size-10" />}
      </AvatarFallback>
    </Avatar>
  );
};

const AvatarFormRemoveButton = ({
  className,
  onRemove,
  ...props
}: React.ComponentProps<typeof Button> & { onRemove?: () => void }) => {
  const { t } = useTranslation("common");
  const { image, update, previewUrl, setPreviewUrl } = useAvatarFormContext();

  const { clearErrors } = useFormContext();
  const [uploadStatus] = useMutationState({
    filters: { mutationKey: mutations.upload.mutationKey },
    select: (mutation) => mutation.state.status,
  });

  const remove = useMutation({
    ...mutations.remove,
    onMutate: () => {
      setPreviewUrl(null);
    },
    onSuccess: () => {
      setPreviewUrl(null);
      onRemove?.();
    },
  });

  return (
    previewUrl &&
    uploadStatus !== "pending" && (
      <Button
        variant="outline"
        size="icon"
        className={cn(
          "bg-background dark:bg-background hover:bg-muted absolute -top-1 -right-1 size-6 rounded-full",
          className,
        )}
        disabled={remove.isPending}
        onClick={() => {
          clearErrors();
          remove.mutate({
            image,
            update,
          });
        }}
        {...props}
      >
        <Icons.X className="size-3.5" />
        <span className="sr-only">{t("remove")}</span>
      </Button>
    )
  );
};

const AvatarFormErrorMessage = (props: React.ComponentProps<"span">) => {
  const _avatarSchema = useAvatarFormSchema();
  const { formState } = useFormContext<z.infer<typeof _avatarSchema>>();

  if (!formState.errors.avatar) {
    return null;
  }

  return (
    <span
      className={cn("text-destructive text-xs", props.className)}
      {...props}
    >
      {formState.errors.avatar.message}
    </span>
  );
};

export {
  AvatarForm,
  AvatarFormInput,
  AvatarFormPreview,
  AvatarFormRemoveButton,
  AvatarFormErrorMessage,
};
