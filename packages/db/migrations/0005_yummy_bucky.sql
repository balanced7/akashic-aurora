ALTER TABLE "customer" DROP CONSTRAINT "customers_pkey";--> statement-breakpoint
ALTER TABLE "customer" ADD COLUMN "id" text PRIMARY KEY NOT NULL;--> statement-breakpoint
ALTER TABLE "customer" ADD CONSTRAINT "customer_userId_unique" UNIQUE("user_id");