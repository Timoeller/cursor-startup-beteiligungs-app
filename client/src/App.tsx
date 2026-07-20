import { useEffect, useState } from "react";
import {
  addShareholder,
  fetchCapTable,
  type CapTableSummary,
  type ShareClass,
} from "./api.js";

export function App() {
  const [capTable, setCapTable] = useState<CapTableSummary | null>(null);
  const [name, setName] = useState("");
  const [shares, setShares] = useState("");
  const [shareClass, setShareClass] = useState<ShareClass>("common");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCapTable()
      .then(setCapTable)
      .catch((e) => setError(String(e)));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const sharesNum = Number(shares);
    if (!name.trim() || !Number.isInteger(sharesNum) || sharesNum <= 0) {
      setError("Enter a name and a positive whole number of shares.");
      return;
    }
    try {
      const updated = await addShareholder({ name: name.trim(), shares: sharesNum, shareClass });
      setCapTable(updated);
      setName("");
      setShares("");
      setShareClass("common");
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <main className="container">
      <header>
        <h1>Beteiligungs-App</h1>
        <p className="subtitle">Startup cap table &amp; equity participation</p>
      </header>

      <section className="card">
        <h2>Add shareholder</h2>
        <form onSubmit={handleSubmit} className="form">
          <label>
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Seed Investor"
              aria-label="name"
            />
          </label>
          <label>
            Shares
            <input
              value={shares}
              onChange={(e) => setShares(e.target.value)}
              placeholder="e.g. 1000"
              inputMode="numeric"
              aria-label="shares"
            />
          </label>
          <label>
            Class
            <select
              value={shareClass}
              onChange={(e) => setShareClass(e.target.value as ShareClass)}
              aria-label="shareClass"
            >
              <option value="common">Common</option>
              <option value="preferred">Preferred</option>
              <option value="option">Option</option>
            </select>
          </label>
          <button type="submit">Add</button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <div className="cap-header">
          <h2>Cap table</h2>
          {capTable && (
            <span className="totals">
              {capTable.totalShareholders} holders · {capTable.totalShares.toLocaleString()} shares
            </span>
          )}
        </div>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Class</th>
              <th className="num">Shares</th>
              <th className="num">Ownership</th>
            </tr>
          </thead>
          <tbody>
            {capTable?.entries.map((e) => (
              <tr key={e.id}>
                <td>{e.name}</td>
                <td>
                  <span className={`badge ${e.shareClass}`}>{e.shareClass}</span>
                </td>
                <td className="num">{e.shares.toLocaleString()}</td>
                <td className="num">{e.ownershipPct}%</td>
              </tr>
            ))}
            {capTable?.entries.length === 0 && (
              <tr>
                <td colSpan={4} className="empty">
                  No shareholders yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
