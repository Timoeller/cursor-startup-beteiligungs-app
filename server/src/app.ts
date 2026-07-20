import cors from "cors";
import express, { type Express } from "express";
import { z } from "zod";
import { CapTable } from "./capTable.js";

const shareholderSchema = z.object({
  name: z.string().min(1, "name is required"),
  shares: z.number().int().positive("shares must be a positive integer"),
  shareClass: z.enum(["common", "preferred", "option"]).default("common"),
});

export function createApp(): Express {
  const app = express();
  app.use(cors());
  app.use(express.json());

  const capTable = new CapTable([
    { name: "Founder A", shares: 6000, shareClass: "common" },
    { name: "Founder B", shares: 4000, shareClass: "common" },
  ]);

  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.get("/api/cap-table", (_req, res) => {
    res.json(capTable.summary());
  });

  app.post("/api/shareholders", (req, res) => {
    const parsed = shareholderSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({ error: parsed.error.flatten() });
      return;
    }
    const { name, shares, shareClass } = parsed.data;
    const shareholder = capTable.addShareholder(name, shares, shareClass);
    res.status(201).json({ shareholder, capTable: capTable.summary() });
  });

  app.delete("/api/shareholders/:id", (req, res) => {
    const removed = capTable.removeShareholder(req.params.id);
    if (!removed) {
      res.status(404).json({ error: "shareholder not found" });
      return;
    }
    res.json({ capTable: capTable.summary() });
  });

  return app;
}
