import { describe, expect, it } from "vitest";
import { initialFilter } from "./select";
import { onlyQueryChanged, readUrlState } from "./url";

describe("readUrlState", () => {
  it("returns defaults for an empty query", () => {
    const s = readUrlState("");
    expect(s.mode).toBe("pool");
    expect(s.page).toBe(1);
    expect(s.filter).toEqual(initialFilter);
  });

  it("parses every field", () => {
    const s = readUrlState("?q=robot&src=qbitai&sort=source&official=1&dated=1&mode=brief&page=3");
    expect(s.filter.q).toBe("robot");
    expect(s.filter.src).toBe("qbitai");
    expect(s.filter.sort).toBe("source");
    expect(s.filter.official).toBe(true);
    expect(s.filter.dated).toBe(true);
    expect(s.mode).toBe("brief");
    expect(s.page).toBe(3);
  });

  it("falls back on invalid sort and page", () => {
    const s = readUrlState("?sort=bogus&page=-2");
    expect(s.filter.sort).toBe("time");
    expect(s.page).toBe(1);
  });
});

describe("onlyQueryChanged", () => {
  const base = readUrlState("?q=a&src=qbitai");

  it("is true when only the query string changes", () => {
    expect(onlyQueryChanged(base, { ...base, filter: { ...base.filter, q: "b" } })).toBe(true);
  });

  it("is false when another filter changes", () => {
    expect(onlyQueryChanged(base, { ...base, filter: { ...base.filter, src: "all" } })).toBe(false);
  });

  it("is false when the page changes", () => {
    expect(onlyQueryChanged(base, { ...base, page: 2 })).toBe(false);
  });
});
