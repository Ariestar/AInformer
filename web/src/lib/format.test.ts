import { describe, expect, it } from "vitest";
import { fmtDate, tierName } from "./format";

describe("fmtDate", () => {
  it("keeps only the date part", () => {
    expect(fmtDate("2026-10-28T06:15:43+00:00")).toBe("2026-10-28");
  });

  it("labels missing dates", () => {
    expect(fmtDate(null)).toBe("无日期");
  });
});

describe("tierName", () => {
  it("expands names by default", () => {
    expect(tierName("official")).toBe("官方源");
    expect(tierName("media")).toBe("媒体源");
    expect(tierName("aggregator")).toBe("聚合源");
  });

  it("shortens names on request", () => {
    expect(tierName("official", true)).toBe("官方");
    expect(tierName("media", true)).toBe("媒体");
    expect(tierName("aggregator", true)).toBe("聚合");
  });
});
