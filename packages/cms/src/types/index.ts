import type { CollectionType, ContentCollection } from "../collections";
import type { SortOrder } from "@akashic-labs/shared/constants";

export const ContentStatus = {
  DRAFT: "draft",
  PUBLISHED: "published",
} as const;

export const ContentTag = {
  LEARNING: "learning",
  SKILLS: "skills",
  PROGRESS: "progress",
  PRODUCT: "product",
  DEVELOPMENT: "development",
  PROTOTYPE: "prototype",
  LAUNCH: "launch",
} as const;

export type ContentStatus = (typeof ContentStatus)[keyof typeof ContentStatus];
export type ContentTag = (typeof ContentTag)[keyof typeof ContentTag];

type ContentCollectionItem<T extends CollectionType> =
  ContentCollection[T][number];

export type GetContentItems = <T extends CollectionType>(args: {
  collection: T;
  status?: ContentStatus;
  tags?: ContentCollectionItem<T> extends { tags: ContentTag[] }
    ? ContentTag[]
    : never;
  locale?: string;
  sortBy?: keyof ContentCollectionItem<T>;
  sortOrder?: SortOrder;
}) => {
  count: number;
  items: ContentCollectionItem<T>[];
};

export type GetContentItemBySlug = <T extends CollectionType>(args: {
  collection: T;
  slug: string;
  status?: ContentStatus;
  locale?: string;
}) => ContentCollectionItem<T> | null;
