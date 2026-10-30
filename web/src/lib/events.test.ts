import { describe, expect, it } from "vitest";
import { groupItems, tierBreakdown } from "./events";
import type { Item } from "./types";

function makeItem(over: Partial<Item> = {}): Item {
  return {
    id: "id-1",
    source_id: "s1",
    source_name: "Source A",
    tier: "media",
    title: "Title",
    url: "https://a.com/1",
    published: "2026-10-28T00:00:00+00:00",
    summary: "",
    cluster_id: "c1",
    event_id: "e1",
    event_size: 1,
    is_primary: true,
    weight: 0.5,
    ...over,
  };
}

describe("groupItems", () => {
  it("groups items sharing an event_id", () => {
    const items = [
      makeItem({ id: "a", event_id: "e1", event_size: 2, is_primary: true, tier: "official" }),
      makeItem({
        id: "b",
        event_id: "e1",
        event_size: 2,
        is_primary: false,
        url: "https://a.com/2",
      }),
      makeItem({ id: "c", event_id: "e2", event_size: 1, url: "https://a.com/3" }),
    ];
    const groups = groupItems(items, new Set());
    expect(groups).toHaveLength(2);
    const e1 = groups.find((g) => g.event_id === "e1");
    if (!e1) throw new Error("expected event e1");
    expect(e1.size).toBe(2);
    expect(e1.items.map((i) => i.id)).toEqual(["a", "b"]);
  });

  it("puts the primary source first", () => {
    const items = [
      makeItem({
        id: "a",
        event_id: "e1",
        event_size: 2,
        is_primary: false,
        url: "https://a.com/2",
      }),
      makeItem({
        id: "b",
        event_id: "e1",
        event_size: 2,
        is_primary: true,
        url: "https://a.com/3",
      }),
    ];
    const groups = groupItems(items, new Set());
    expect(groups[0].primary.id).toBe("b");
  });

  it("flags official presence as trusted", () => {
    const withOfficial = [
      makeItem({ id: "a", event_id: "e1", event_size: 2, tier: "aggregator" }),
      makeItem({
        id: "b",
        event_id: "e1",
        event_size: 2,
        tier: "official",
        url: "https://a.com/2",
      }),
    ];
    expect(groupItems(withOfficial, new Set())[0].hasOfficial).toBe(true);

    const noOfficial = [
      makeItem({ id: "a", event_id: "e1", event_size: 2, tier: "media" }),
      makeItem({
        id: "b",
        event_id: "e1",
        event_size: 2,
        tier: "aggregator",
        url: "https://a.com/2",
      }),
    ];
    expect(groupItems(noOfficial, new Set())[0].hasOfficial).toBe(false);
  });

  it("splits a flagged event into singletons", () => {
    const items = [
      makeItem({ id: "a", event_id: "e1", event_size: 2, is_primary: true }),
      makeItem({
        id: "b",
        event_id: "e1",
        event_size: 2,
        is_primary: false,
        url: "https://a.com/2",
      }),
    ];
    const groups = groupItems(items, new Set(["e1"]));
    expect(groups).toHaveLength(2);
    expect(groups.every((g) => g.size === 1)).toBe(true);
  });

  it("sorts groups by newest first", () => {
    const items = [
      makeItem({
        id: "a",
        event_id: "older",
        event_size: 1,
        published: "2026-10-26T00:00:00+00:00",
      }),
      makeItem({
        id: "b",
        event_id: "newer",
        event_size: 1,
        published: "2026-10-28T00:00:00+00:00",
        url: "https://a.com/2",
      }),
    ];
    const groups = groupItems(items, new Set());
    expect(groups.map((g) => g.event_id)).toEqual(["newer", "older"]);
  });

  it("keeps the newest date across members", () => {
    const items = [
      makeItem({ id: "a", event_id: "e1", event_size: 2, published: "2026-10-26T00:00:00+00:00" }),
      makeItem({
        id: "b",
        event_id: "e1",
        event_size: 2,
        published: "2026-10-28T00:00:00+00:00",
        url: "https://a.com/2",
      }),
    ];
    expect(groupItems(items, new Set())[0].newest).toBe("2026-10-28T00:00:00+00:00");
  });
});

describe("tierBreakdown", () => {
  it("lists only present tiers in order", () => {
    const group = groupItems(
      [
        makeItem({ id: "a", event_id: "e1", event_size: 3, tier: "official" }),
        makeItem({
          id: "b",
          event_id: "e1",
          event_size: 3,
          tier: "official",
          url: "https://a.com/2",
        }),
        makeItem({ id: "c", event_id: "e1", event_size: 3, tier: "media", url: "https://a.com/3" }),
      ],
      new Set(),
    )[0];
    expect(tierBreakdown(group)).toBe("官方 2 · 媒体 1");
  });

  it("omits empty tiers", () => {
    const group = groupItems(
      [makeItem({ id: "a", event_id: "e1", event_size: 1, tier: "aggregator" })],
      new Set(),
    )[0];
    expect(tierBreakdown(group)).toBe("聚合 1");
  });
});
