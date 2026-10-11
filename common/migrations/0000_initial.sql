CREATE TABLE `cost_entries` (
	`id` text PRIMARY KEY NOT NULL,
	`item_id` text NOT NULL,
	`type` text NOT NULL,
	`quantity` real NOT NULL,
	`unit` text NOT NULL,
	`dollars` real NOT NULL,
	`cached` integer DEFAULT false NOT NULL,
	`detail` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`item_id`) REFERENCES `items`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "cost_entries_type_check" CHECK("cost_entries"."type" IN ('firecrawl', 'describer', 'tts')),
	CONSTRAINT "cost_entries_unit_check" CHECK("cost_entries"."unit" IN ('credits', 'calls', 'seconds')),
	CONSTRAINT "cost_entries_cached_check" CHECK("cost_entries"."cached" IN (0, 1)),
	CONSTRAINT "cost_entries_detail_check" CHECK("cost_entries"."detail" IS NULL OR json_valid("cost_entries"."detail"))
);
--> statement-breakpoint
CREATE INDEX `ix_cost_entries_item_id` ON `cost_entries` (`item_id`);--> statement-breakpoint
CREATE TABLE `items` (
	`id` text PRIMARY KEY NOT NULL,
	`url` text NOT NULL,
	`title` text,
	`voice` text NOT NULL,
	`status` text NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`queued_at` text NOT NULL,
	`workflow_instance_id` text,
	`current_step` text,
	`extraction_domain` text,
	`recipe_version_id` text,
	`retry_count` integer DEFAULT 0 NOT NULL,
	`duration` real,
	`audio_format` text,
	`units` text,
	`degradations` text,
	`error` text,
	FOREIGN KEY (`recipe_version_id`) REFERENCES `recipe_versions`(`id`) ON UPDATE no action ON DELETE no action,
	CONSTRAINT "items_status_check" CHECK("items"."status" IN ('queued', 'generating', 'ready', 'failed')),
	CONSTRAINT "items_units_check" CHECK("items"."units" IS NULL OR json_valid("items"."units")),
	CONSTRAINT "items_degradations_check" CHECK("items"."degradations" IS NULL OR json_valid("items"."degradations"))
);
--> statement-breakpoint
CREATE TABLE `recipe_versions` (
	`id` text PRIMARY KEY NOT NULL,
	`domain` text NOT NULL,
	`version` integer NOT NULL,
	`script` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `recipe_versions_domain_version_unique` ON `recipe_versions` (`domain`,`version`);