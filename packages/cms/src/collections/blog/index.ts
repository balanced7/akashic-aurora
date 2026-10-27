import { defineCollection } from "@content-collections/core";
import { compileMDX } from "@content-collections/mdx";
import rehypeShiki from "@shikijs/rehype";
import readingTime from "reading-time";
import * as z from "zod";

import { ContentStatus, ContentTag } from "../../types";
import { getLastModifiedAt } from "../../utils";

export const blog = defineCollection({
  name: "blog",
  directory: "src/collections/blog/content",
  include: "**/*.mdx",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    thumbnail: z.string(),
    publishedAt: z.coerce.date(),
    tags: z.array(z.enum(ContentTag)),
    status: z.enum(ContentStatus),
  }),
  transform: async (document, context) => {
    const mdx = await compileMDX(context, document, {
      rehypePlugins: [
        [
          rehypeShiki,
          {
            /* see https://shiki.matsu.io/themes for available themes */
            theme: "one-dark-pro",
          },
        ],
      ],
    });

    const lastModifiedAt = await context.cache(
      document._meta.filePath,
      getLastModifiedAt,
    );

    const timeToRead = readingTime(document.content).time;

    return {
      ...document,
      mdx,
      lastModifiedAt,
      timeToRead,
      slug: document._meta.directory,
      locale: document._meta.fileName.split(".")[0],
    };
  },
});
