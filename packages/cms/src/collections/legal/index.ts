import { defineCollection } from "@content-collections/core";
import { compileMDX } from "@content-collections/mdx";
import * as z from "zod";

import { ContentStatus } from "../../types";
import { getLastModifiedAt } from "../../utils";

export const legal = defineCollection({
  name: "legal",
  directory: "src/collections/legal/content",
  include: "**/*.mdx",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    status: z.enum(ContentStatus),
  }),
  transform: async (document, context) => {
    const mdx = await compileMDX(context, document);
    const lastModifiedAt = await context.cache(
      document._meta.filePath,
      getLastModifiedAt,
    );

    return {
      ...document,
      mdx,
      lastModifiedAt,
      slug: document._meta.directory,
      locale: document._meta.fileName.split(".")[0],
    };
  },
});
