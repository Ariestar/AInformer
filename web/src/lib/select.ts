import type { Item, SortKey } from "./types";

export interface FilterState {
  q: string;
  src: string;
  official: boolean;
  dated: boolean;
  sort: SortKey;
}

export const initialFilter: FilterState = {
  q: "",
  src: "all",
  official: false,
  dated: false,
  sort: "time",
};

// 有日期的按时间倒序，没日期的垫底；按来源排序时用中文排序规则。
export function filterItems(items: Item[], s: FilterState): Item[] {
  const q = s.q.trim().toLowerCase();
  const out = items.filter((it) => {
    if (s.official && it.tier !== "official") return false;
    if (s.dated && !it.published) return false;
    if (s.src !== "all" && it.source_id !== s.src) return false;
    if (q) {
      const hay = `${it.title} ${it.summary || ""} ${it.source_name}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  if (s.sort === "time") {
    out.sort((a, b) => {
      if (!a.published && !b.published) return 0;
      if (!a.published) return 1;
      if (!b.published) return -1;
      return a.published < b.published ? 1 : -1;
    });
  } else if (s.sort === "source") {
    out.sort((a, b) => a.source_name.localeCompare(b.source_name, "zh"));
  }
  return out;
}

export function sourceOptions(items: Item[]): Array<{ id: string; name: string }> {
  const seen = new Map<string, string>();
  for (const it of items) seen.set(it.source_id, it.source_name);
  return [...seen.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, "zh"));
}
