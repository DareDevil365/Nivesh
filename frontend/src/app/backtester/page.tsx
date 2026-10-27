"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { EquityCurveChart } from "@/components/EquityCurveChart";
import { EmptyState, number, money, download, csvCell } from "@/lib/research";

type Indicator = "RSI" | "SMA_CROSS" | "EMA_CROSS" | "MACD" | "BOLLINGER";
type Rule = {
  indicator: Indicator;
  condition: string;
  value: number;
  params: {
    period: number;
    fast_period: number;
    slow_period: number;
    signal_period: number;
    std_dev: number;
  };
};
type Form = {
  ticker: string;
  entry_rule: Rule;
  exit_rule: Rule;
  position_sizing: { type: string; amount: number };
  stop_loss_pct: number;
  take_profit_pct: number;
  cost_bps: number;
  slippage_bps: number;
  date_range: { start: string; end: string };
};
const dateString = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
function defaults(): Form {
  const today = new Date(),
    start = new Date(today);
  start.setFullYear(today.getFullYear() - 3);
  const params = {
    period: 14,
    fast_period: 20,
    slow_period: 50,
    signal_period: 9,
    std_dev: 2,
  };
  return {
    ticker: "RELIANCE.NS",
    entry_rule: {
      indicator: "RSI",
      condition: "crosses_below",
      value: 30,
      params: { ...params },
    },
    exit_rule: {
      indicator: "RSI",
      condition: "crosses_above",
      value: 70,
      params: { ...params },
    },
    position_sizing: { type: "fixed_capital", amount: 100000 },
    stop_loss_pct: 5,
    take_profit_pct: 15,
    cost_bps: 10,
    slippage_bps: 5,
    date_range: { start: dateString(start), end: dateString(today) },
  };
}
function Numeric({
  label,
  value,
  onChange,
  min = 0,
  max,
  step = "any",
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: string;
}) {
  return (
    <label className="block text-xs text-mutedText">
      {label}
      <input
        aria-label={label}
        required
        type="number"
        min={min}
        max={max}
        step={step}
        value={Number.isFinite(value) ? value : ""}
        onChange={(e) =>
          onChange(e.target.value === "" ? NaN : Number(e.target.value))
        }
        className="block w-full mt-2 bg-bg border border-border rounded-lg p-2 text-neutralText"
      />
    </label>
  );
}
function RuleBuilder({
  title,
  rule,
  change,
  entry,
}: {
  title: string;
  rule: Rule;
  change: (r: Rule) => void;
  entry: boolean;
}) {
  const choose = (indicator: Indicator) =>
    change({
      ...rule,
      indicator,
      condition:
        indicator === "BOLLINGER"
          ? entry
            ? "touches_lower"
            : "touches_upper"
          : indicator === "RSI"
            ? entry
              ? "crosses_below"
              : "crosses_above"
            : entry
              ? "crosses_above"
              : "crosses_below",
      params: {
        ...rule.params,
        period: indicator === "BOLLINGER" ? 20 : 14,
        fast_period: indicator === "MACD" ? 12 : 20,
        slow_period: indicator === "MACD" ? 26 : 50,
      },
    });
  const p = (key: keyof Rule["params"], v: number) =>
    change({ ...rule, params: { ...rule.params, [key]: v } });
  return (
    <fieldset className="rounded-lg border border-border p-4 space-y-4">
      <legend className="px-2 text-sm font-semibold">{title}</legend>
      <label className="block text-xs text-mutedText">
        Indicator
        <select
          aria-label={`${title} indicator`}
          value={rule.indicator}
          onChange={(e) => choose(e.target.value as Indicator)}
          className="block w-full mt-2 bg-bg border border-border rounded-lg p-2"
        >
          {["RSI", "SMA_CROSS", "EMA_CROSS", "MACD", "BOLLINGER"].map((i) => (
            <option key={i}>{i}</option>
          ))}
        </select>
      </label>
      <label className="block text-xs text-mutedText">
        Condition
        <select
          aria-label={`${title} condition`}
          value={rule.condition}
          onChange={(e) => change({ ...rule, condition: e.target.value })}
          className="block w-full mt-2 bg-bg border border-border rounded-lg p-2"
        >
          {(rule.indicator === "BOLLINGER"
            ? ["touches_lower", "touches_upper"]
            : ["crosses_above", "crosses_below"]
          ).map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </label>
      {rule.indicator === "RSI" && (
        <Numeric
          label={`${title} RSI threshold`}
          value={rule.value}
          max={100}
          onChange={(v) => change({ ...rule, value: v })}
        />
      )}
      {["RSI", "BOLLINGER"].includes(rule.indicator) ? (
        <Numeric
          label={`${title} lookback period`}
          value={rule.params.period}
          min={2}
          max={250}
          step="1"
          onChange={(v) => p("period", v)}
        />
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <Numeric
            label={`${title} fast period`}
            value={rule.params.fast_period}
            min={2}
            max={250}
            step="1"
            onChange={(v) => p("fast_period", v)}
          />
          <Numeric
            label={`${title} slow period`}
            value={rule.params.slow_period}
            min={3}
            max={300}
            step="1"
            onChange={(v) => p("slow_period", v)}
          />
        </div>
      )}
      {rule.indicator === "MACD" && (
        <Numeric
          label={`${title} signal period`}
          value={rule.params.signal_period}
          min={2}
          max={100}
          step="1"
          onChange={(v) => p("signal_period", v)}
        />
      )}
      {rule.indicator === "BOLLINGER" && (
        <Numeric
          label={`${title} standard deviations`}
          value={rule.params.std_dev}
          min={0.1}
          max={5}
          onChange={(v) => p("std_dev", v)}
        />
      )}
    </fieldset>
  );
}

export default function BacktesterPage() {
  const [form, setForm] = useState<Form>(defaults);
  const [prompt, setPrompt] = useState("");
  const [parsing, setParsing] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [results, setResults] = useState<any>(null);
  const [submitted, setSubmitted] = useState("");
  const parse = async () => {
    setParsing(true);
    setError("");
    setNotice("");
    try {
      const data = await api.post("/api/backtest/parse", { text: prompt });
      const { scenario_label, ...strategy } = data.strategy_json;
      setForm(strategy);
      setWarnings(data.warnings || []);
      setNotice("Rules parsed. Review all parameters below before running.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setParsing(false);
    }
  };
  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setError("");
    setResults(null);
    try {
      const data = await api.post("/api/backtest", form);
      setResults(data);
      setSubmitted(JSON.stringify(form));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };
  const save = () => {
    try {
      localStorage.setItem("nivesh-saved-strategy", JSON.stringify(form));
      setNotice("Strategy saved in this browser.");
    } catch {
      setError("Browser storage is unavailable. Export the strategy instead.");
    }
  };
  const load = () => {
    try {
      const stored = localStorage.getItem("nivesh-saved-strategy");
      if (!stored) throw new Error("No saved strategy in this browser.");
      const parsed = JSON.parse(stored);
      if (
        !parsed.entry_rule?.params ||
        !parsed.exit_rule?.params ||
        !parsed.date_range ||
        !parsed.position_sizing
      )
        throw new Error("Saved strategy format is invalid.");
      setForm(parsed);
      setNotice("Saved parameters loaded. Review before running.");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const exportTrades = () =>
    download(
      `${results.ticker}-backtest-trades.csv`,
      [
        [
          "ticker",
          "buy_date",
          "buy_price",
          "sell_date",
          "sell_price",
          "qty",
          "costs",
          "pnl",
          "exit_reason",
        ],
        ...results.trade_log.map((t: any) => [
          results.ticker,
          t.entry_date,
          t.entry_price,
          t.exit_date,
          t.exit_price,
          t.shares,
          t.costs,
          t.pnl,
          t.exit_reason,
        ]),
      ]
        .map((r) => r.map(csvCell).join(","))
        .join("\n"),
      "text/csv",
    );
  return (
    <div className="space-y-6">
      <section className="bg-surface border border-border rounded-card p-6 space-y-4">
        <p className="text-xs text-primary uppercase tracking-wider">
          Test an idea with transparent assumptions
        </p>
        <h1 className="text-3xl font-heading font-bold">Strategy backtester</h1>
        <p className="text-sm text-mutedText">
          Long-only daily stock simulation. Closing signals execute at the next
          opening price. Costs, slippage, warm-up history and stop handling are
          included. Historical returns are not a forecast.
        </p>
        <label className="block text-sm">
          Describe one supported strategy
          <textarea
            aria-label="Strategy description"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            maxLength={2000}
            rows={3}
            placeholder="RELIANCE.NS: buy when RSI 14 crosses below 30, sell above 70, stop loss 5%, from 2021-01-01 to 2025-12-31"
            className="block w-full mt-2 bg-bg border border-border rounded-lg p-3 text-xs"
          />
        </label>
        <button
          type="button"
          onClick={parse}
          disabled={parsing || prompt.trim().length < 5}
          className="rounded-lg border border-primary/40 px-4 py-2 text-xs text-primary disabled:opacity-40"
        >
          {parsing ? "Parsing…" : "Fill builder from description"}
        </button>
        <p className="text-[11px] text-mutedText">
          Supported: RSI, SMA/EMA crossovers, MACD, Bollinger bands. Use
          explicit symbols and dates. Multi-indicator combinations, short
          selling, derivatives and intraday execution are not supported.
        </p>
      </section>
      {notice && (
        <p role="status" className="text-sm text-primary">
          {notice}
        </p>
      )}
      {error && (
        <div
          role="alert"
          className="rounded-lg border border-negative/30 bg-negative/10 p-4 text-sm text-negative"
        >
          {error}
        </div>
      )}
      {warnings.map((w) => (
        <p className="text-xs text-amber-300" key={w}>
          {w}
        </p>
      ))}
      <form
        onSubmit={run}
        className="bg-surface border border-border rounded-card p-5 space-y-5"
      >
        <div className="flex flex-wrap gap-2 items-center justify-between">
          <h2 className="font-semibold">Strategy builder</h2>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={save}
              className="border border-border rounded-lg p-2 text-xs"
            >
              Save parameters
            </button>
            <button
              type="button"
              onClick={load}
              className="border border-border rounded-lg p-2 text-xs"
            >
              Load saved
            </button>
            <button
              type="button"
              onClick={() =>
                download(
                  "nivesh-strategy.json",
                  JSON.stringify(form, null, 2),
                  "application/json",
                )
              }
              className="border border-border rounded-lg p-2 text-xs"
            >
              Export JSON
            </button>
          </div>
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          <label className="text-xs text-mutedText">
            Exchange symbol
            <input
              aria-label="Backtest ticker"
              required
              maxLength={30}
              value={form.ticker}
              onChange={(e) =>
                setForm({ ...form, ticker: e.target.value.toUpperCase() })
              }
              className="block mt-2 w-full bg-bg border border-border rounded-lg p-2 text-neutralText"
            />
          </label>
          {(["start", "end"] as const).map((k) => (
            <label key={k} className="text-xs text-mutedText">
              {k === "start" ? "Start date" : "End date"}
              <input
                aria-label={`${k} date`}
                type="date"
                min="1994-11-03"
                max={dateString(new Date())}
                required
                value={form.date_range[k]}
                onChange={(e) =>
                  setForm({
                    ...form,
                    date_range: { ...form.date_range, [k]: e.target.value },
                  })
                }
                className="block mt-2 w-full bg-bg border border-border rounded-lg p-2 text-neutralText"
              />
            </label>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 items-center text-xs text-mutedText">
          <span>Historical range:</span>
          {[
            ["2008 crisis", "2008-01-01", "2009-03-31"],
            ["COVID crash", "2020-02-01", "2020-08-31"],
            ["Demonetization", "2016-11-01", "2017-01-31"],
          ].map(([label, start, end]) => (
            <button
              type="button"
              key={label}
              onClick={() => setForm({ ...form, date_range: { start, end } })}
              className="rounded border border-border px-3 py-1.5"
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            onClick={() =>
              setForm({ ...form, date_range: defaults().date_range })
            }
            className="rounded border border-border px-3 py-1.5"
          >
            Last 3 years
          </button>
        </div>
        <div className="grid md:grid-cols-2 gap-5">
          <RuleBuilder
            title="Entry"
            rule={form.entry_rule}
            entry
            change={(rule) => setForm({ ...form, entry_rule: rule })}
          />
          <RuleBuilder
            title="Exit"
            rule={form.exit_rule}
            entry={false}
            change={(rule) => setForm({ ...form, exit_rule: rule })}
          />
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <Numeric
            label="Initial capital (₹)"
            min={1}
            max={1e9}
            value={form.position_sizing.amount}
            onChange={(v) =>
              setForm({
                ...form,
                position_sizing: { type: "fixed_capital", amount: v },
              })
            }
          />
          <Numeric
            label="Stop loss (%) · 0 disables"
            max={99}
            value={form.stop_loss_pct}
            onChange={(v) => setForm({ ...form, stop_loss_pct: v })}
          />
          <Numeric
            label="Take profit (%) · 0 disables"
            max={1000}
            value={form.take_profit_pct}
            onChange={(v) => setForm({ ...form, take_profit_pct: v })}
          />
          <Numeric
            label="Costs per side (bps)"
            max={500}
            value={form.cost_bps}
            onChange={(v) => setForm({ ...form, cost_bps: v })}
          />
          <Numeric
            label="Slippage per side (bps)"
            max={500}
            value={form.slippage_bps}
            onChange={(v) => setForm({ ...form, slippage_bps: v })}
          />
        </div>
        <p className="text-xs text-mutedText">
          1 basis point = 0.01%. Cost input is an aggregate assumption, not an
          automatic calculation of Indian taxes or broker charges. Whole
          adjusted units; all available capital is reinvested.
        </p>
        <button
          disabled={running}
          className="rounded-lg bg-primary text-white font-semibold px-6 py-3 text-sm disabled:opacity-50"
        >
          {running ? "Running simulation…" : "Run backtest"}
        </button>
      </form>
      {running && (
        <EmptyState title="Fetching history and executing strategy…">
          Older date ranges depend on the instrument's listing date and provider
          coverage.
        </EmptyState>
      )}
      {results && (
        <section className="space-y-5">
          <div className="bg-surface border border-border rounded-card p-5 space-y-4">
            <h2 className="font-semibold text-lg">
              Results · {results.ticker}
            </h2>
            <p className="text-xs text-mutedText">
              Actual data range: {results.actual_start} to {results.actual_end}.
              Total costs and slippage: {money(results.total_costs)}.
            </p>
            {submitted !== JSON.stringify(form) && (
              <p className="text-xs text-amber-300">
                Builder parameters have changed. These are the results of your
                previous run.
              </p>
            )}
            {results.warnings.map((w: string) => (
              <p key={w} className="text-xs text-amber-300">
                {w}
              </p>
            ))}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {[
                ["Total return", results.total_return_pct, "%"],
                ["CAGR", results.cagr, "%"],
                ["Max drawdown", results.max_drawdown_pct, "%"],
                ["Sharpe (rf = 0)", results.sharpe_ratio, ""],
                ["Win rate", results.win_rate_pct, "%"],
                ["Closed trades", results.total_trades, ""],
              ].map(([label, value, unit]) => (
                <div key={String(label)} className="p-3 bg-bg rounded-lg">
                  <p className="text-xs text-mutedText">{label}</p>
                  <p className="text-xl font-heading mt-2">
                    {number(value as number, String(unit))}
                  </p>
                </div>
              ))}
            </div>
            <details className="text-xs">
              <summary className="cursor-pointer text-primary">
                Execution assumptions & limitations
              </summary>
              <ul className="mt-3 space-y-2 text-mutedText">
                {Object.entries(results.assumptions).map(([k, v]) => (
                  <li key={k}>
                    <strong>{k.replaceAll("_", " ")}: </strong>
                    {String(v)}
                  </li>
                ))}
              </ul>
            </details>
          </div>
          <EquityCurveChart
            data={results.equity_curve}
            initialCapital={results.initial_capital}
          />
          <div className="bg-surface border border-border rounded-card p-5 space-y-4">
            <div className="flex justify-between gap-3">
              <h3 className="font-semibold">Closed trade log</h3>
              <button
                onClick={exportTrades}
                disabled={!results.trade_log.length}
                className="text-xs text-primary border border-border rounded-lg p-2 disabled:opacity-40"
              >
                Export trades
              </button>
            </div>
            {!results.trade_log.length ? (
              <EmptyState title="No entry signals triggered">
                This is a valid result. Try another period or rule; unsupported
                indicators are rejected instead of silently ignored.
              </EmptyState>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[700px] text-xs text-left">
                  <thead>
                    <tr>
                      {[
                        "Entry",
                        "Exit",
                        "Buy price",
                        "Sell price",
                        "Units",
                        "Net P&L",
                        "Reason",
                      ].map((k) => (
                        <th key={k} className="p-2 text-mutedText">
                          {k}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.trade_log.map((t: any, i: number) => (
                      <tr key={i} className="border-t border-border">
                        <td className="p-2">{t.entry_date}</td>
                        <td className="p-2">{t.exit_date}</td>
                        <td className="p-2">{money(t.entry_price)}</td>
                        <td className="p-2">{money(t.exit_price)}</td>
                        <td className="p-2">{t.shares}</td>
                        <td
                          className={`p-2 ${t.pnl >= 0 ? "text-positive" : "text-negative"}`}
                        >
                          {money(t.pnl)}
                        </td>
                        <td className="p-2 text-mutedText">{t.exit_reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
