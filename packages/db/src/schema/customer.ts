import { pgEnum, pgTable, text, timestamp } from "drizzle-orm/pg-core";

import { generateId } from "@akashic-labs/shared/utils";

import {
  createInsertSchema,
  createSelectSchema,
  createUpdateSchema,
} from "../lib/zod";

import { user } from "./auth";

import type * as z from "zod";

export const billingStatusEnum = pgEnum("status", [
  "active",
  "canceled",
  "incomplete",
  "incomplete_expired",
  "past_due",
  "paused",
  "trialing",
  "unpaid",
]);

export const pricingPlanTypeEnum = pgEnum("plan", [
  "free",
  "premium",
  "enterprise",
]);

export const customer = pgTable("customer", {
  id: text().primaryKey().$defaultFn(generateId),
  userId: text()
    .references(() => user.id, {
      onDelete: "cascade",
    })
    .notNull()
    .unique(),
  customerId: text().notNull().unique(),
  status: billingStatusEnum(),
  plan: pricingPlanTypeEnum(),
  createdAt: timestamp().notNull().defaultNow(),
  updatedAt: timestamp()
    .notNull()
    .$onUpdate(() => new Date()),
});

export const insertCustomerSchema = createInsertSchema(customer);
export const selectCustomerSchema = createSelectSchema(customer);
export const updateCustomerSchema = createUpdateSchema(customer);

export type InsertCustomer = z.infer<typeof insertCustomerSchema>;
export type SelectCustomer = z.infer<typeof selectCustomerSchema>;
export type UpdateCustomer = z.infer<typeof updateCustomerSchema>;
