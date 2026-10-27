"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, number, money, download } from "@/lib/research";
const TEMPLATE =
  "ticker,buy_date,buy_price,sell_date,sell_price,qty,costs\nRELIANCE.NS,2024-01-02,2500,2024-02-02,2600,10,20\nTCS.NS,2024-01-10,3800,2024-03-01,3650,5,15\nINFY.NS,2024-02-05,1600,2024-03-05,1700,12,18\n";
export default function BehaviorPage() {
  const [broker, setBroker] = useState("auto");
  const [parsed, setParsed] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [filename, setFilename] = useState("");
  const [demo, setDemo] = useState(false);
  const parse = async (text: string, name: string, isDemo = false) => {
    setBusy(true);
    setError("");
    setParsed(null);
    setReport(null);
    setFilename(name);
    setDemo(isDemo);
    try {
      const result = await api.post("/api/behavior/upload", {
        csv_text: text,
        broker: isDemo ? "generic" : broker,
      });
      setParsed(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    if (file.size > 2_000_000) {
      setError("CSV files must be smaller than 2 MB.");
      return;
    }
    await parse(await file.text(), file.name);
  };
  const analyze = async () => {
    if (!parsed) return;
    setBusy(true);
    setError("");
    try {
      setReport(
        await api.post("/api/behavior/analyze", { trades: parsed.trades }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const m = report?.metrics;
  return (
    <div className="space-y-6">
      <section className="rounded-card bg-surface border border-border p-6 space-y-4">
        <p className="text-xs text-primary uppercase tracking-wider">
          Review your execution
        </p>
        <h1 className="text-3xl font-heading font-bold">
          Trade journal analysis
        </h1>
        <p className="text-sm text-mutedText max-w-3xl">
          Import closed trades or match buy/sell executions using FIFO. Review
          the imported sample before analyzing. Metrics describe your recorded
          trades; they do not diagnose psychology or infer unrealized positions.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() =>
              download(
                "nivesh-closed-trades-template.csv",
                TEMPLATE,
                "text/csv",
              )
            }
            className="border border-border rounded-lg px-4 py-2 text-xs"
          >
            Download CSV template
          </button>
          <button
            disabled={busy}
            onClick={() => parse(TEMPLATE, "Demonstration sample", true)}
            className="border border-border rounded-lg px-4 py-2 text-xs"
          >
            Explore labelled demo
          </button>
        </div>
      </section>
      <section className="rounded-card bg-surface border border-border p-5 space-y-4">
        <h2 className="font-semibold">Import CSV</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="text-sm">
            Export format
            <select
              aria-label="Broker format"
              value={broker}
              onChange={(e) => setBroker(e.target.value)}
              disabled={busy}
              className="block w-full mt-2 bg-bg border border-border rounded-lg p-3 text-xs"
            >
              {[
                ["auto", "Detect headers"],
                ["zerodha", "Zerodha executions"],
                ["groww", "Groww / closed trades"],
                ["generic", "Generic template"],
              ].map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            CSV file (up to 2 MB)
            <input
              aria-label="Trade CSV file"
              type="file"
              accept=".csv,text/csv"
              disabled={busy}
              onChange={(e) => {
                void upload(e.target.files?.[0]);
                e.target.value = "";
              }}
              className="block w-full mt-2 bg-bg border border-border rounded-lg p-2 text-xs"
            />
          </label>
        </div>
        <p className="text-xs text-mutedText">
          Supported execution fields: symbol, trade_date, trade_type, quantity,
          price. Closed-trade fields: ticker, buy_date, buy_price, sell_date,
          sell_price, qty, optional costs. Prices and quantities must be
          positive. Dates may be YYYY-MM-DD, DD-MM-YYYY or DD/MM/YYYY. Trades
          are processed by the backend and are not saved to the research
          database or sent to an AI provider.
        </p>
      </section>
      {error && (
        <div
          role="alert"
          className="rounded-card border border-negative/30 bg-negative/10 p-4 text-sm text-negative"
        >
          {error}
        </div>
      )}
      {busy && <EmptyState title="Processing trade records…" />}
      {parsed && (
        <section className="rounded-card bg-surface border border-border p-5 space-y-4">
          <div className="flex flex-wrap justify-between gap-3">
            <h2 className="font-semibold">Review matched records</h2>
            {demo && (
              <span className="text-xs text-amber-300 border border-amber-300/30 px-3 py-1 rounded-full">
                DEMO · synthetic sample, not your history
              </span>
            )}
          </div>
          <p className="text-xs text-mutedText">
            {filename} · {parsed.row_count} input rows · {parsed.trade_count}{" "}
            closed observations · {parsed.matching}
          </p>
          {parsed.warnings.map((w: string) => (
            <p key={w} className="text-xs text-amber-300">
              {w}
            </p>
          ))}
          {parsed.errors.length > 0 && (
            <details className="text-xs">
              <summary className="cursor-pointer text-primary">
                View excluded-row errors ({parsed.errors.length})
              </summary>
              <ul className="mt-2 space-y-1">
                {parsed.errors.map((e: any) => (
                  <li key={e.line}>
                    Row {e.line}: {e.message}
                  </li>
                ))}
              </ul>
            </details>
          )}
          <div className="overflow-x-auto">
            <table className="text-xs w-full min-w-[600px] text-left">
              <thead>
                <tr>
                  {[
                    "Ticker",
                    "Bought",
                    "Sold",
                    "Buy price",
                    "Sell price",
                    "Quantity",
                  ].map((k) => (
                    <th className="p-2 text-mutedText" key={k}>
                      {k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {parsed.trades.slice(0, 20).map((t: any, i: number) => (
                  <tr className="border-t border-border" key={i}>
                    <td className="p-2">{t.ticker}</td>
                    <td className="p-2">{t.buy_date}</td>
                    <td className="p-2">{t.sell_date}</td>
                    <td className="p-2">{money(t.buy_price)}</td>
                    <td className="p-2">{money(t.sell_price)}</td>
                    <td className="p-2">{number(t.qty)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {parsed.trades.length > 20 && (
            <p className="text-xs text-mutedText">
              Preview shows the first 20 observations. Analysis includes all{" "}
              {parsed.trades.length} validated observations.
            </p>
          )}
          <button
            onClick={analyze}
            disabled={busy}
            className="bg-primary text-white rounded-lg px-5 py-2 text-sm font-semibold disabled:opacity-50"
          >
            Analyze matched trades
          </button>
        </section>
      )}
      {m && (
        <section className="rounded-card bg-surface border border-border p-5 space-y-5">
          <h2 className="font-semibold text-lg">
            {demo ? "Demo statistics" : "Closed-trade statistics"}
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              ["Closed observations", m.total_trades, ""],
              ["Win rate", m.win_rate_pct, "%"],
              ["Mean trade return", m.expectancy_pct, "%"],
              ["Average loss / average win", m.loss_aversion_ratio, "x"],
              ["Loser / winner holding days", m.disposition_score, "x"],
              ["Size variation · CV", m.position_sizing_cv, ""],
              ["Size increases within 2 days of loss", m.revenge_score, "%"],
              ["Observations per week", m.trades_per_week, ""],
            ].map(([label, value, unit]) => (
              <div
                key={String(label)}
                className="rounded-lg bg-bg border border-border p-4"
              >
                <p className="text-xs text-mutedText">{label}</p>
                <p className="text-2xl font-heading mt-2">
                  {number(value as number | null, String(unit))}
                </p>
              </div>
            ))}
          </div>
          <p className="text-sm">
            Net recorded P&L: {money(m.total_pnl)} · Supplied costs:{" "}
            {money(m.total_costs)}
          </p>
          <ul className="space-y-2 text-sm text-mutedText">
            {report.flags.map((flag: string) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
          <p className="text-xs text-mutedText">
            {report.narrative} Flat observations are included in the sample but
            are neither wins nor losses. A matched lot is not necessarily an
            independent investment decision.
          </p>
        </section>
      )}
    </div>
  );
}
