export type ShareClass = "common" | "preferred" | "option";

export interface CapTableEntry {
  id: string;
  name: string;
  shares: number;
  shareClass: ShareClass;
  ownershipPct: number;
}

export interface CapTableSummary {
  totalShares: number;
  totalShareholders: number;
  entries: CapTableEntry[];
}

export async function fetchCapTable(): Promise<CapTableSummary> {
  const res = await fetch("/api/cap-table");
  if (!res.ok) throw new Error("Failed to load cap table");
  return res.json();
}

export async function addShareholder(input: {
  name: string;
  shares: number;
  shareClass: ShareClass;
}): Promise<CapTableSummary> {
  const res = await fetch("/api/shareholders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error("Failed to add shareholder");
  const data = await res.json();
  return data.capTable as CapTableSummary;
}
