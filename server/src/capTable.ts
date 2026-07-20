import { randomUUID } from "node:crypto";

export type ShareClass = "common" | "preferred" | "option";

export interface Shareholder {
  id: string;
  name: string;
  shares: number;
  shareClass: ShareClass;
  createdAt: string;
}

export interface CapTableEntry extends Shareholder {
  ownershipPct: number;
}

export interface CapTableSummary {
  totalShares: number;
  totalShareholders: number;
  entries: CapTableEntry[];
}

/**
 * In-memory cap table. Kept intentionally simple (no DB) so the dev
 * environment runs with zero external services. Swap for a real store later.
 */
export class CapTable {
  private shareholders: Shareholder[] = [];

  constructor(seed: Array<Omit<Shareholder, "id" | "createdAt">> = []) {
    for (const s of seed) {
      this.addShareholder(s.name, s.shares, s.shareClass);
    }
  }

  addShareholder(name: string, shares: number, shareClass: ShareClass): Shareholder {
    const shareholder: Shareholder = {
      id: randomUUID(),
      name,
      shares,
      shareClass,
      createdAt: new Date().toISOString(),
    };
    this.shareholders.push(shareholder);
    return shareholder;
  }

  removeShareholder(id: string): boolean {
    const before = this.shareholders.length;
    this.shareholders = this.shareholders.filter((s) => s.id !== id);
    return this.shareholders.length < before;
  }

  totalShares(): number {
    return this.shareholders.reduce((sum, s) => sum + s.shares, 0);
  }

  summary(): CapTableSummary {
    const total = this.totalShares();
    const entries: CapTableEntry[] = this.shareholders.map((s) => ({
      ...s,
      ownershipPct: total === 0 ? 0 : Number(((s.shares / total) * 100).toFixed(4)),
    }));
    return {
      totalShares: total,
      totalShareholders: this.shareholders.length,
      entries,
    };
  }
}
