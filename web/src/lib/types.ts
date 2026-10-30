// 与 schema/pool.schema.json 一一对应。改字段必须同时改 schema，否则 export.py 会拦住构建。
export type Tier = "official" | "media" | "aggregator";
export type SortKey = "time" | "source";
export type ViewMode = "pool" | "brief";

export interface Item {
  id: string;
  source_id: string;
  source_name: string;
  tier: Tier;
  title: string;
  url: string;
  published: string | null;
  summary: string;
  cluster_id: string;
  weight: number;
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
  items: Item[];
}
