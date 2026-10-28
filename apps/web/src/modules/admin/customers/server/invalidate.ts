"use server";

import { revalidatePath } from "next/cache";

import { pathsConfig } from "~/config/paths";

// eslint-disable-next-line @typescript-eslint/require-await
export const invalidateCustomers = async () =>
  revalidatePath(pathsConfig.admin.customers.index);
