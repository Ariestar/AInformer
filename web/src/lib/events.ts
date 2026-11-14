import type { Item } from "./types";

// 事件视图的数据结构：把散条目按 event_id 归成「一件事」。
// 可信度只有两档，落在 hasOfficial 上 —— 有官方源 vs 无官方源。

export interface EventGroup {
  event_id: string;
  items: Item[];
  primary: Item;
  hasOfficial: boolean;
  size: number;
  newest: string | null;
}

// split 是用户点了「这不是同一件事」的事件集合：这些事件不归并，每条各成一组。
// 反馈只在前端本地生效（localStorage 持久化），不上传、不改数据。
export function groupItems(items: Item[], split: ReadonlySet<string>): EventGroup[] {
  const map = new Map<string, Item[]>();
  for (const it of items) {
    const key = split.has(it.event_id) ? `split:${it.id}` : it.event_id;
    const arr = map.get(key);
    if (arr) {
      arr.push(it);
    } else {
      map.set(key, [it]);
    }
  }

  const groups: EventGroup[] = [];
  for (const members of map.values()) {
    members.sort((a, b) => {
      if (a.is_primary !== b.is_primary) return a.is_primary ? -1 : 1;
      const pa = a.published ?? "";
      const pb = b.published ?? "";
      if (pa !== pb) return pa < pb ? 1 : -1;
      return 0;
    });
    const primary = members[0];
    let newest: string | null = null;
    for (const m of members) {
      if (m.published && (newest === null || m.published > newest)) newest = m.published;
    }
    groups.push({
      event_id: primary.event_id,
      items: members,
      primary,
      hasOfficial: members.some((m) => m.tier === "official"),
      size: members.length,
      newest,
    });
  }

  groups.sort((a, b) => {
    const na = a.newest ?? "";
    const nb = b.newest ?? "";
    if (na !== nb) return na < nb ? 1 : -1;
    return 0;
  });
  return groups;
}

// 事件内来源构成，形如「官方 2 · 媒体 1 · 聚合 1」，用于一行看清来源厚度。
export function tierBreakdown(g: EventGroup): string {
  const n: Record<string, number> = { official: 0, media: 0, aggregator: 0 };
  for (const m of g.items) n[m.tier] += 1;
  const parts: string[] = [];
  if (n.official > 0) parts.push(`官方 ${n.official}`);
  if (n.media > 0) parts.push(`媒体 ${n.media}`);
  if (n.aggregator > 0) parts.push(`聚合 ${n.aggregator}`);
  return parts.join(" · ");
}
