ALTER TABLE "organization" ALTER COLUMN "slug" SET NOT NULL;--> statement-breakpoint
ALTER TABLE "invitation" ADD COLUMN "created_at" timestamp DEFAULT now() NOT NULL;