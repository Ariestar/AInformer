// 与 schema/pool.schema.json 一一对应。改字段必须同时改 schema，否则 export.py 会拦住构建。
export type Tier = "official" | "media" | "aggregator";
export type SortKey = "time" | "source";
export type ViewMode = "daily" | "pool" | "brief";
export type PoolView = "events" | "items";

export interface Item {
  id: string;
  source_id: string;
  source_name: string;
  tier: Tier;
  title: string;
  url: string;
  published: string | null;
  summary: string;
  event_id: string;
  is_primary: boolean;
  weight: number;
}

export type SourceState = "ok" | "error" | "stale" | "empty";

// 源健康由 bin/export.py 算好，前端只渲染。
export interface SourceRow {
  id: string;
  name: string;
  state: SourceState;
  kept: number;
  newest: string | null;
  staleDays: number;
  error: string | null;
}

export interface HealthSummary {
  total: number;
  problemCount: number;
  alerts: string[];
  rows: SourceRow[];
}

export interface Stats {
  sources_total: number;
  sources_ok: number;
  raw_items: number;
  after_dedup: number;
}

export interface PoolPayload {
  generated_at: string;
  window_days: number;
  stats: Stats;
  health: HealthSummary;
  items: Item[];
}

export interface DailyEvent {
  event_id: string;
  title: string;
  size: number;
  tier: Tier;
  url: string;
  published: string | null;
}

export interface DailySection {
  key: string;
  name: string;
  summary: string | null;
  events: DailyEvent[];
}

export interface DailyPayload {
  date: string;
  generated_at: string;
  coverage: {
    events: number;
    items: number;
    sources_ok: number;
    sources_total: number;
  };
  sections: DailySection[];
  gaps: string[];
}
