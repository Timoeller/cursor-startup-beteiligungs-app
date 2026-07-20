import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App.js";

const sampleCapTable = {
  totalShares: 10000,
  totalShareholders: 2,
  entries: [
    { id: "1", name: "Founder A", shares: 6000, shareClass: "common", ownershipPct: 60 },
    { id: "2", name: "Founder B", shares: 4000, shareClass: "common", ownershipPct: 40 },
  ],
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      json: async () => sampleCapTable,
    })),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the cap table loaded from the API", async () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Beteiligungs-App" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Founder A")).toBeInTheDocument();
      expect(screen.getByText("60%")).toBeInTheDocument();
    });
  });
});
