import { type SQL, sql } from "drizzle-orm";
import {
  type AnySQLiteColumn,
  check,
  index,
  integer,
  real,
  sqliteTable,
  text,
  unique,
} from "drizzle-orm/sqlite-core";
import { ITEM_STATUS } from "../item.ts";
import { COST_TYPE, COST_UNIT } from "../ledger.ts";
import type { Degradation, Unit } from "../units.ts";
import type { Step } from "../workflow.ts";
import { mintId } from "./mint-id.ts";

// These helpers stay beside the tables because only the schema's CHECKs use them.
const valuesOf = <T extends Record<string, string>>(map: T) =>
  Object.values(map) as [T[keyof T], ...T[keyof T][]];

// A text enum is only a type to drizzle, so the CHECK that keeps D1 to the same values is spelled
// out beside it.
const oneOf = (column: AnySQLiteColumn, map: Record<string, string>): SQL =>
  sql`${column} IN (${sql.raw(
    valuesOf(map)
      .map((value) => `'${value}'`)
      .join(", "),
  )})`;

const jsonOrNull = (column: AnySQLiteColumn): SQL =>
  sql`${column} IS NULL OR json_valid(${column})`;

const now = () => new Date().toISOString();

export const recipeVersions = sqliteTable(
  "recipe_versions",
  {
    id: text()
      .primaryKey()
      .$defaultFn(() => mintId("rcp", 8)),
    domain: text().notNull(),
    version: integer().notNull(),
    script: text().notNull(),
    created_at: text().notNull().$defaultFn(now),
  },
  (table) => [unique().on(table.domain, table.version)],
);

export const items = sqliteTable(
  "items",
  {
    id: text()
      .primaryKey()
      .$defaultFn(() => mintId("itm", 8)),
    url: text().notNull(),
    title: text(),
    voice: text().notNull(),
    status: text({ enum: valuesOf(ITEM_STATUS) }).notNull(),
    created_at: text().notNull().$defaultFn(now),
    updated_at: text().notNull().$defaultFn(now).$onUpdate(now),
    queued_at: text().notNull().$defaultFn(now),
    workflow_instance_id: text(),
    current_step: text().$type<Step>(),
    extraction_domain: text(),
    recipe_version_id: text().references(() => recipeVersions.id),
    retry_count: integer().notNull().default(0),
    duration: real(),
    audio_format: text(),
    units: text({ mode: "json" }).$type<Unit[]>(),
    degradations: text({ mode: "json" }).$type<Degradation[]>(),
    error: text(),
  },
  (table) => [
    check("items_status_check", oneOf(table.status, ITEM_STATUS)),
    check("items_units_check", jsonOrNull(table.units)),
    check("items_degradations_check", jsonOrNull(table.degradations)),
  ],
);

export const costEntries = sqliteTable(
  "cost_entries",
  {
    id: text()
      .primaryKey()
      .$defaultFn(() => mintId("cst", 12)),
    item_id: text()
      .notNull()
      .references(() => items.id),
    type: text({ enum: valuesOf(COST_TYPE) }).notNull(),
    quantity: real().notNull(),
    unit: text({ enum: valuesOf(COST_UNIT) }).notNull(),
    dollars: real().notNull(),
    cached: integer({ mode: "boolean" }).notNull().default(false),
    detail: text({ mode: "json" }).$type<Record<string, unknown>>(),
    created_at: text().notNull().$defaultFn(now),
  },
  (table) => [
    check("cost_entries_type_check", oneOf(table.type, COST_TYPE)),
    check("cost_entries_unit_check", oneOf(table.unit, COST_UNIT)),
    check("cost_entries_cached_check", sql`${table.cached} IN (0, 1)`),
    check("cost_entries_detail_check", jsonOrNull(table.detail)),
    index("ix_cost_entries_item_id").on(table.item_id),
  ],
);
