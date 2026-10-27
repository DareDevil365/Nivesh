"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import StockSearchInput from "@/components/StockSearchInput";
import { api } from "@/lib/api";
import {
  useResource,
  ResourceState,
  EmptyState,
  number,
  money,
  dateTime,
  download,
  csvCell,
} from "@/lib/research";
export default function WatchlistPage() {
  const resource = useResource("/api/watchlist");
  const alerts = useResource("/api/watchlist/alerts");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [ticker, setTicker] = useState("RELIANCE.NS");
  const [condition, setCondition] = useState("PRICE_ABOVE");
  const [threshold, setThreshold] = useState("1000");
  const refresh = () => {
    resource.reload();
    alerts.reload();
  };
  const add = async (symbol: string) => {
    setNotice("");
    try {
      await api.post("/api/watchlist/item", { ticker: symbol });
      setNotice(`${symbol} saved.`);
      resource.reload();
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  const remove = async (symbol: string) => {
    try {
      await api.delete(
        `/api/watchlist/item?ticker=${encodeURIComponent(symbol)}`,
      );
      setNotice(`${symbol} removed.`);
      resource.reload();
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setNotice("");
    try {
      await api.post("/api/watchlist/alerts", {
        ticker,
        condition,
        threshold: Number(threshold),
      });
      setNotice("Condition saved. Evaluated when you reload this page.");
      alerts.reload();
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setSaving(false);
    }
  };
  const removeAlert = async (id: string) => {
    try {
      await api.delete(`/api/watchlist/alerts/${encodeURIComponent(id)}`);
      alerts.reload();
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  const exportList = () =>
    download(
      "nivesh-watchlist.csv",
      [
        [
          "Ticker",
          "Company",
          "Price INR",
          "PE",
          "ROE %",
          "Quote date",
          "Fetched at",
        ],
        ...(resource.data?.items || []).map((s: any) => [
          s.ticker,
          s.name,
          s.current_price,
          s.pe,
          s.roe,
          s.quote_as_of,
          s.fetched_at,
        ]),
      ]
        .map((r) => r.map(csvCell).join(","))
        .join("\n"),
      "text/csv",
    );
  return (
    <div className="space-y-6">
      <section className="rounded-card border border-border bg-surface p-6 space-y-4">
        <p className="text-xs text-primary uppercase tracking-wider">
          Your research workspace
        </p>
        <h1 className="text-3xl font-heading font-bold">
          Watchlist & conditions
        </h1>
        <p className="text-sm text-mutedText">
          Saved on this server and isolated to this browser's signed workspace
          cookie. Records survive server restarts. Clearing cookies loses
          access; account sync and background notifications are not enabled.
        </p>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="w-full max-w-lg">
            <StockSearchInput
              placeholder="Search a company to track"
              buttonText="Add stock"
              onSelectTicker={add}
            />
          </div>
          <button
            onClick={refresh}
            className="border border-border rounded-lg px-4 py-2 text-xs"
          >
            Reload quotes & conditions
          </button>
          <button
            onClick={exportList}
            className="border border-border rounded-lg px-4 py-2 text-xs"
          >
            Export watchlist
          </button>
        </div>
        {notice && (
          <p role="status" className="text-sm text-primary">
            {notice}
          </p>
        )}
      </section>
      <ResourceState resource={resource}>
        {resource.data && (
          <section className="rounded-card border border-border bg-surface p-5 space-y-4">
            <h2 className="font-semibold">
              Tracked companies ({resource.data.count})
            </h2>
            {!resource.data.items.length ? (
              <EmptyState title="Start your watchlist">
                Search above or save a company from its research page.
              </EmptyState>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[700px] text-xs text-left">
                  <thead>
                    <tr className="text-mutedText">
                      <th className="p-3">Company</th>
                      <th className="p-3">Price</th>
                      <th className="p-3">Change</th>
                      <th className="p-3">P/E</th>
                      <th className="p-3">ROE</th>
                      <th className="p-3">Quote as of (IST)</th>
                      <th className="p-3">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resource.data.items.map((s: any) => (
                      <tr key={s.ticker} className="border-t border-border">
                        <td className="p-3">
                          <Link
                            href={`/stock/${encodeURIComponent(s.ticker)}`}
                            className="font-semibold hover:text-primary"
                          >
                            {s.name}
                          </Link>
                          <p className="text-[10px] text-mutedText">
                            {s.ticker} {!s.available && "· Quote unavailable"}
                          </p>
                        </td>
                        <td className="p-3">{money(s.current_price)}</td>
                        <td className="p-3">{number(s.day_change_pct, "%")}</td>
                        <td className="p-3">{number(s.pe, "x")}</td>
                        <td className="p-3">{number(s.roe, "%")}</td>
                        <td className="p-3 text-mutedText">
                          {dateTime(s.quote_as_of)}
                        </td>
                        <td className="p-3">
                          <button
                            aria-label={`Remove ${s.ticker}`}
                            onClick={() => remove(s.ticker)}
                            className="text-negative"
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </ResourceState>
      <div className="grid lg:grid-cols-[300px_minmax(0,1fr)] gap-5">
        <form
          onSubmit={create}
          className="rounded-card border border-border bg-surface p-5 space-y-4 self-start"
        >
          <h2 className="font-semibold">Track a condition</h2>
          <label className="block text-xs">
            Ticker
            <input
              aria-label="Condition ticker"
              required
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="mt-2 w-full bg-bg border border-border rounded-lg p-2"
            />
          </label>
          <label className="block text-xs">
            Condition
            <select
              aria-label="Condition type"
              value={condition}
              onChange={(e) => {
                setCondition(e.target.value);
                setThreshold(
                  e.target.value === "VOLUME_SPIKE"
                    ? "2"
                    : e.target.value.startsWith("RSI")
                      ? "70"
                      : "1000",
                );
              }}
              className="mt-2 w-full bg-bg border border-border rounded-lg p-2"
            >
              {[
                "PRICE_ABOVE",
                "PRICE_BELOW",
                "RSI_ABOVE",
                "RSI_BELOW",
                "VOLUME_SPIKE",
              ].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="block text-xs">
            Threshold{" "}
            {condition.startsWith("PRICE")
              ? "(₹)"
              : condition === "VOLUME_SPIKE"
                ? "(times 20-day average volume)"
                : "(0–100)"}
            <input
              aria-label="Condition threshold"
              required
              type="number"
              min="0"
              max={condition.startsWith("RSI") ? "100" : undefined}
              step="any"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="mt-2 w-full bg-bg border border-border rounded-lg p-2"
            />
          </label>
          <button
            disabled={saving}
            className="w-full bg-primary text-white rounded-lg py-2 text-xs font-semibold disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save condition"}
          </button>
          <p className="text-[11px] text-mutedText">
            Price uses the latest cached quote. RSI and volume use the most
            recent daily bar. Conditions are checked on reload; no email or push
            alerts are sent.
          </p>
        </form>
        <ResourceState resource={alerts}>
          <section className="rounded-card border border-border bg-surface p-5 space-y-4 min-w-0">
            <h2 className="font-semibold">Saved conditions</h2>
            {!alerts.data?.alerts?.length ? (
              <EmptyState title="No conditions saved">
                Set a price, RSI or volume condition to review here.
              </EmptyState>
            ) : (
              alerts.data.alerts.map((a: any) => (
                <div
                  key={a.id}
                  className="rounded-lg border border-border bg-bg p-4 space-y-2"
                >
                  <div className="flex justify-between gap-3">
                    <Link
                      className="font-semibold text-sm hover:text-primary"
                      href={`/stock/${a.ticker}`}
                    >
                      {a.ticker}
                    </Link>
                    <button
                      aria-label={`Delete condition ${a.ticker}`}
                      onClick={() => removeAlert(a.id)}
                      className="text-xs text-negative"
                    >
                      Delete
                    </button>
                  </div>
                  <p className="text-xs">
                    {a.condition.replaceAll("_", " ")} · {number(a.threshold)}
                  </p>
                  <p
                    className={`text-sm ${a.triggered === true ? "text-amber-300" : "text-mutedText"}`}
                  >
                    {a.triggered == null
                      ? "Data unavailable"
                      : a.triggered
                        ? "Condition met"
                        : "Condition not met"}{" "}
                    · Observed {number(a.observed_value)}
                  </p>
                  <p className="text-[11px] text-mutedText">
                    Checked against data as of {dateTime(a.checked_at)}
                  </p>
                </div>
              ))
            )}
          </section>
        </ResourceState>
      </div>
    </div>
  );
}
