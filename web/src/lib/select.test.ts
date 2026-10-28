import { describe, expect, it } from "vitest";
import { filterItems, initialFilter, sourceOptions } from "./select";
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
    weight: 0.5,
    ...over,
  };
}

const items: Item[] = [
  makeItem({ id: "a", title: "Alpha release", published: "2026-10-28T00:00:00+00:00" }),
  makeItem({
    id: "b",
    title: "Beta research",
    published: "2026-10-26T00:00:00+00:00",
    tier: "official",
    source_id: "s2",
    source_name: "Source B",
    summary: "about GPT",
  }),
  makeItem({ id: "c", title: "Gamma", published: null, tier: "aggregator" }),
];

describe("filterItems", () => {
  it("returns everything with the default filter", () => {
    expect(filterItems(items, initialFilter)).toHaveLength(3);
  });

  it("matches the title", () => {
    const out = filterItems(items, { ...initialFilter, q: "alpha" });
    expect(out.map((i) => i.id)).toEqual(["a"]);
  });

  it("matches the summary", () => {
    const out = filterItems(items, { ...initialFilter, q: "gpt" });
    expect(out.map((i) => i.id)).toEqual(["b"]);
  });

  it("matches the source name", () => {
    const out = filterItems(items, { ...initialFilter, q: "source b" });
    expect(out.map((i) => i.id)).toEqual(["b"]);
  });

  it("filters by official tier", () => {
    const out = filterItems(items, { ...initialFilter, official: true });
    expect(out.map((i) => i.id)).toEqual(["b"]);
  });

  it("filters undated items out", () => {
    const out = filterItems(items, { ...initialFilter, dated: true });
    expect(out.map((i) => i.id)).toEqual(["a", "b"]);
  });

  it("filters by source id", () => {
    const out = filterItems(items, { ...initialFilter, src: "s2" });
    expect(out.map((i) => i.id)).toEqual(["b"]);
  });

  it("sorts newest first and pushes undated to the end", () => {
    const out = filterItems(items, { ...initialFilter, sort: "time" });
    expect(out.map((i) => i.id)).toEqual(["a", "b", "c"]);
  });

  it("sorts by source name with chinese collation", () => {
    const out = filterItems(items, { ...initialFilter, sort: "source" });
    expect(out.map((i) => i.id)).toEqual(["a", "c", "b"]);
  });

  it("does not mutate the input array", () => {
    const snapshot = [...items];
    filterItems(items, { ...initialFilter, sort: "source" });
    expect(items).toEqual(snapshot);
  });
});

describe("sourceOptions", () => {
  it("deduplicates and sorts sources", () => {
    expect(sourceOptions(items)).toEqual([
      { id: "s1", name: "Source A" },
      { id: "s2", name: "Source B" },
    ]);
  });
});
