import type { Item, SourceHealth } from "./types";

// 源健康：把「抓取结果 + 条目池」折算成每个源的状态。
// 三类问题：抓取失败、断更超过 30 天、60 天窗口内零新增。

export type SourceState = "ok" | "error" | "stale" | "empty";

export interface SourceRow {
  id: string;
  name: string;
  state: SourceState;
  kept: number;
  newest: string | null;
  staleDays: number; // 最新条目距今多少天；无条目时为 -1
  error: string | null;
}

export interface HealthSummary {
  total: number;
  problemCount: number;
  alerts: string[];
  rows: SourceRow[];
}

export const STALE_DAYS = 30;
const DAY_MS = 86_400_000;
const RANK: Record<SourceState, number> = { error: 0, stale: 1, empty: 2, ok: 3 };

export function computeHealth(
  sources: SourceHealth[],
  items: Item[],
  nowIso: string,
): HealthSummary {
  const now = new Date(nowIso).getTime();

  const newestBy = new Map<string, string>();
  for (const it of items) {
    if (!it.published) continue;
    const cur = newestBy.get(it.source_id);
    if (!cur || it.published > cur) newestBy.set(it.source_id, it.published);
  }

  const rows: SourceRow[] = sources.map((s) => {
    const newest = newestBy.get(s.id) ?? null;
    const staleDays = newest ? Math.floor((now - new Date(newest).getTime()) / DAY_MS) : -1;
    let state: SourceState = "ok";
    if (!s.ok) state = "error";
    else if (!newest) state = "empty";
    else if (staleDays > STALE_DAYS) state = "stale";
    return { id: s.id, name: s.name, state, kept: s.kept, newest, staleDays, error: s.error };
  });

  rows.sort((a, b) => RANK[a.state] - RANK[b.state] || a.name.localeCompare(b.name, "zh"));

  const alerts: string[] = [];
  for (const r of rows) {
    if (r.state === "error") alerts.push(`${r.name} 本轮抓取失败`);
    else if (r.state === "stale") alerts.push(`${r.name} 已 ${r.staleDays} 天未更新`);
    else if (r.state === "empty") alerts.push(`${r.name} 60 天内零新增`);
  }

  return { total: sources.length, problemCount: alerts.length, alerts, rows };
}
