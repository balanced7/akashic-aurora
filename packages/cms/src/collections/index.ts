import { SortOrder } from "@akashic-labs/shared/constants";

import { allBlogs, allLegals } from "../../.content-collections/generated";
import { ContentStatus } from "../types";

import type {
  ContentTag,
  GetContentItemBySlug,
  GetContentItems,
} from "../types";

export const CollectionType = {
  LEGAL: "legal",
  BLOG: "blog",
} as const;

export type CollectionType =
  (typeof CollectionType)[keyof typeof CollectionType];

export const content = {
  [CollectionType.LEGAL]: allLegals,
  [CollectionType.BLOG]: allBlogs,
} as const;

export type ContentCollection = typeof content;

type ContentCollectionItem<T extends CollectionType> =
  ContentCollection[T][number];

const hasTags = <T extends CollectionType>(
  item: ContentCollectionItem<T>,
): item is ContentCollectionItem<T> & { tags: ContentTag[] } => {
  return "tags" in item;
};

const sortItems = <T extends CollectionType>(
  items: ContentCollectionItem<T>[],
  sortBy: keyof ContentCollectionItem<T>,
  sortOrder: SortOrder,
) => {
  return items.sort((a, b) => {
    const aValue = a[sortBy];
    const bValue = b[sortBy];

    if (!aValue || !bValue) {
      return 0;
    }

    if (typeof aValue === "string" && typeof bValue === "string") {
      return sortOrder === SortOrder.ASCENDING
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    }

    if (typeof aValue === "number" && typeof bValue === "number") {
      return sortOrder === SortOrder.ASCENDING
        ? aValue - bValue
        : bValue - aValue;
    }

    if (aValue instanceof Date && bValue instanceof Date) {
      return sortOrder === SortOrder.ASCENDING
        ? aValue.getTime() - bValue.getTime()
        : bValue.getTime() - aValue.getTime();
    }

    return 0;
  });
};

export const getContentItems: GetContentItems = ({
  collection,
  status = ContentStatus.PUBLISHED,
  tags = [] as ContentTag[],
  sortBy,
  sortOrder = SortOrder.DESCENDING,
  locale,
}) => {
  const items = content[collection];

  const itemsWithTags = items.filter(
    (item) =>
      !tags.length ||
      !hasTags(item) ||
      item.tags.some((tag) => tags.includes(tag)),
  );

  const itemsWithStatus = itemsWithTags.filter(
    (item) => item.status === status,
  );

  const itemsWithLocale = itemsWithStatus.filter(
    (item) => !locale || item.locale === locale,
  );

  const sortedItems = sortBy
    ? sortItems(itemsWithLocale, sortBy, sortOrder)
    : itemsWithLocale;

  return {
    count: sortedItems.length,
    items: sortedItems,
  };
};

export const getContentItemBySlug: GetContentItemBySlug = ({
  collection,
  slug,
  status = ContentStatus.PUBLISHED,
  locale,
}) =>
  content[collection].find(
    (item) =>
      item.slug === slug && item.status === status && item.locale === locale,
  ) ?? null;
