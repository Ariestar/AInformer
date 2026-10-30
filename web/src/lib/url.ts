import { type FilterState, initialFilter } from "./select";
import type { SortKey, ViewMode } from "./types";

export interface UrlState {
  filter: FilterState;
  mode: ViewMode;
  page: number;
}

const SORTS: readonly string[] = ["time", "source"];

/** 从 location.search 解析页面状态；非法值一律回落到默认，不抛错。 */
export function readUrlState(search: string): UrlState {
  const p = new URLSearchParams(search);
  const sort = p.get("sort") ?? "";
  const page = Number.parseInt(p.get("page") ?? "1", 10);
  return {
    mode: p.get("mode") === "brief" ? "brief" : "pool",
    page: Number.isFinite(page) && page > 0 ? page : 1,
    filter: {
      ...initialFilter,
      q: p.get("q") ?? "",
      src: p.get("src") ?? "all",
      sort: SORTS.includes(sort) ? (sort as SortKey) : "time",
      official: p.get("official") === "1",
      dated: p.get("dated") === "1",
    },
  };
}

function serialize(state: UrlState): string {
  const p = new URLSearchParams();
  if (state.filter.q.trim()) p.set("q", state.filter.q.trim());
  if (state.filter.src !== "all") p.set("src", state.filter.src);
  if (state.filter.sort !== "time") p.set("sort", state.filter.sort);
  if (state.filter.official) p.set("official", "1");
  if (state.filter.dated) p.set("dated", "1");
  if (state.mode === "brief") p.set("mode", "brief");
  if (state.page > 1) p.set("page", String(state.page));
  return p.toString();
}

/** 除搜索词外没有别的变化 → 说明只是打字，用 replace 避免刷历史。 */
export function onlyQueryChanged(prev: UrlState, next: UrlState): boolean {
  const strip = (s: UrlState): UrlState => ({ ...s, filter: { ...s.filter, q: "" } });
  return serialize(strip(prev)) === serialize(strip(next));
}

export function writeUrlState(state: UrlState, historyMode: "push" | "replace"): void {
  const qs = serialize(state);
  const target = qs ? `${location.pathname}?${qs}` : location.pathname;
  if (target === `${location.pathname}${location.search}`) return;
  if (historyMode === "push") history.pushState(null, "", target);
  else history.replaceState(null, "", target);
}
