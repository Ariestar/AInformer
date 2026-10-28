import type { Tier } from "./types";

export function fmtDate(s: string | null): string {
  return s ? s.slice(0, 10) : "无日期";
}

// 源的层级不是二分的：官方一手 > 媒体采写 > 聚合转述。
// 聚合源（AIHOT、橘鸦）是对别人的再筛选，只能当线索，不能当事实依据。
export function tierName(t: Tier, short = false): string {
  if (t === "official") return short ? "官方" : "官方源";
  if (t === "aggregator") return short ? "聚合" : "聚合源";
  return short ? "媒体" : "媒体源";
}
