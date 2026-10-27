import { defineCollection } from "@content-collections/core";
import { compileMDX } from "@content-collections/mdx";
import rehypeShiki from "@shikijs/rehype";
import readingTime from "reading-time";
import remarkGfm from "remark-gfm";
import * as z from "zod";

import { ContentStatus } from "../../types";
import { getLastModifiedAt } from "../../utils";
import { rehypeCitations } from "./rehype-citations";

/** Forest Walks: long-form field notes on how machines work, one walk per directory. */
export const walk = defineCollection({
  name: "walk",
  directory: "src/collections/walk/content",
  include: "**/*.mdx",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    walk: z.number().int().positive(),
    edition: z.string().optional(),
    publishedAt: z.coerce.date(),
    status: z.enum(ContentStatus),
  }),
  transform: async (document, context) => {
    const mdx = await compileMDX(context, document, {
      remarkPlugins: [remarkGfm],
      rehypePlugins: [
        rehypeCitations,
        [rehypeShiki, { theme: "one-dark-pro" }],
      ],
    });

    const lastModifiedAt = await context.cache(
      document._meta.filePath,
      getLastModifiedAt,
    );

    const { time: timeToRead, words } = readingTime(document.content);

    return {
      ...document,
      mdx,
      lastModifiedAt,
      timeToRead,
      words,
      slug: document._meta.directory,
      locale: document._meta.fileName.split(".")[0],
    };
  },
});
