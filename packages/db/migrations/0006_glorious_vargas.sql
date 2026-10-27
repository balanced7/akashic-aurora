ALTER TABLE "customer" ALTER COLUMN "status" SET DATA TYPE text;--> statement-breakpoint
DROP TYPE "public"."status";--> statement-breakpoint
CREATE TYPE "public"."status" AS ENUM('active', 'canceled', 'incomplete', 'incomplete_expired', 'past_due', 'paused', 'trialing', 'unpaid');--> statement-breakpoint
ALTER TABLE "customer" ALTER COLUMN "status" SET DATA TYPE "public"."status" USING "status"::"public"."status";--> statement-breakpoint
ALTER TABLE "customer" ALTER COLUMN "plan" SET DATA TYPE text;--> statement-breakpoint
DROP TYPE "public"."plan";--> statement-breakpoint
CREATE TYPE "public"."plan" AS ENUM('free', 'premium', 'enterprise');--> statement-breakpoint
ALTER TABLE "customer" ALTER COLUMN "plan" SET DATA TYPE "public"."plan" USING "plan"::"public"."plan";