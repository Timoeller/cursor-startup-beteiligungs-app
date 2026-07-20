import { describe, expect, it } from "vitest";
import { CapTable } from "./capTable.js";

describe("CapTable", () => {
  it("computes ownership percentages from shares", () => {
    const table = new CapTable([
      { name: "Founder A", shares: 6000, shareClass: "common" },
      { name: "Founder B", shares: 4000, shareClass: "common" },
    ]);

    const summary = table.summary();
    expect(summary.totalShares).toBe(10000);
    expect(summary.totalShareholders).toBe(2);
    expect(summary.entries[0].ownershipPct).toBe(60);
    expect(summary.entries[1].ownershipPct).toBe(40);
  });

  it("recomputes percentages after adding a shareholder", () => {
    const table = new CapTable([{ name: "Founder A", shares: 9000, shareClass: "common" }]);
    table.addShareholder("Investor", 1000, "preferred");

    const summary = table.summary();
    expect(summary.totalShares).toBe(10000);
    expect(summary.entries.find((e) => e.name === "Investor")?.ownershipPct).toBe(10);
  });

  it("removes shareholders by id", () => {
    const table = new CapTable();
    const s = table.addShareholder("Temp", 100, "option");
    expect(table.removeShareholder(s.id)).toBe(true);
    expect(table.removeShareholder(s.id)).toBe(false);
    expect(table.summary().totalShareholders).toBe(0);
  });

  it("reports zero ownership when there are no shares", () => {
    const table = new CapTable();
    expect(table.summary().totalShares).toBe(0);
    expect(table.summary().entries).toHaveLength(0);
  });
});
