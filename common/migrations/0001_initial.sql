CREATE TABLE recipe_versions (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL,
  version INTEGER NOT NULL,
  script TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (domain, version)
);

CREATE TABLE items (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT,
  voice TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'generating', 'ready', 'failed')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  queued_at TEXT NOT NULL,
  workflow_instance_id TEXT,
  current_step TEXT,
  extraction_domain TEXT,
  recipe_version_id TEXT REFERENCES recipe_versions (id),
  retry_count INTEGER NOT NULL DEFAULT 0,
  duration REAL,
  audio_format TEXT,
  units TEXT CHECK (units IS NULL OR json_valid(units)),
  degradations TEXT CHECK (degradations IS NULL OR json_valid(degradations)),
  error TEXT
);

CREATE TABLE cost_entries (
  id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL REFERENCES items (id),
  type TEXT NOT NULL CHECK (type IN ('firecrawl', 'describer', 'tts')),
  quantity REAL NOT NULL,
  unit TEXT NOT NULL CHECK (unit IN ('credits', 'calls', 'seconds')),
  dollars REAL NOT NULL,
  cached INTEGER NOT NULL DEFAULT 0 CHECK (cached IN (0, 1)),
  detail TEXT CHECK (detail IS NULL OR json_valid(detail)),
  created_at TEXT NOT NULL
);

CREATE INDEX ix_cost_entries_item_id ON cost_entries (item_id);
