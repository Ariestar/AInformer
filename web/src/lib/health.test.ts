import { describe, expect, it } from "vitest";
import { computeHealth, STALE_DAYS } from "./health";
import type { Item, SourceHealth } from "./types";

function makeSource(over: Partial<SourceHealth> = {}): SourceHealth {
  return { id: "s1", name: "Source A", ok: true, fetched: 1, kept: 1, error: null, ...over };
}

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

const NOW = "2026-10-29T00:00:00+00:00";

describe("computeHealth", () => {
  it("marks a healthy source as ok", () => {
    const rows = computeHealth(
      [makeSource({ id: "s1", name: "Good" })],
      [makeItem({ source_id: "s1", published: "2026-10-28T00:00:00+00:00" })],
      NOW,
    ).rows;
    expect(rows[0].state).toBe("ok");
  });

  it("flags a failed fetch", () => {
    const rows = computeHealth(
      [makeSource({ id: "s1", name: "Broken", ok: false, error: "HTTP 403" })],
      [],
      NOW,
    ).rows;
    expect(rows[0].state).toBe("error");
  });

  it("flags a source with no items in the window", () => {
    const rows = computeHealth([makeSource({ id: "s1", name: "Silent", kept: 0 })], [], NOW).rows;
    expect(rows[0].state).toBe("empty");
  });

  it("flags a stale source older than the threshold", () => {
    const old = new Date(Date.now() - (STALE_DAYS + 10) * 86_400_000).toISOString();
    const rows = computeHealth(
      [makeSource({ id: "s1", name: "Stale" })],
      [makeItem({ source_id: "s1", published: old })],
      NOW,
    ).rows;
    expect(rows[0].state).toBe("stale");
    expect(rows[0].staleDays).toBeGreaterThan(STALE_DAYS);
  });

  it("sorts problems before healthy sources", () => {
    const summary = computeHealth(
      [
        makeSource({ id: "ok", name: "Fine" }),
        makeSource({ id: "bad", name: "Broken", ok: false }),
      ],
      [makeItem({ source_id: "ok" })],
      NOW,
    );
    expect(summary.rows.map((r) => r.id)).toEqual(["bad", "ok"]);
  });

  it("builds human-readable alerts for every problem", () => {
    const summary = computeHealth([makeSource({ id: "bad", name: "Broken", ok: false })], [], NOW);
    expect(summary.problemCount).toBe(1);
    expect(summary.alerts[0]).toContain("Broken");
  });
});
