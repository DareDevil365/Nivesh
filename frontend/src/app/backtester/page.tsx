"use client";

import React, { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { SearchAutocomplete } from "@/components/SearchAutocomplete";
import { EquityCurveChart } from "@/components/EquityCurveChart";
import { api } from "@/lib/api";
import { 
  BrainCircuit, 
  Play, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  CheckCircle2, 
  AlertTriangle,
  History,
  Sliders,
  FileSpreadsheet,
  Zap
} from "lucide-react";

interface BacktestResults {
  error?: string;
  ticker: string;
  initial_capital: number;
  final_capital: number;
  total_return_pct: number;
  cagr: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  total_trades: number;
  win_rate_pct: number;
  trade_log: Array<{
    entry_date: string;
    exit_date: string;
    entry_price: number;
    exit_price: number;
    shares: number;
    pnl: number;
    pnl_pct: number;
    win: boolean;
  }>;
  equity_curve: Array<{
    time: string;
    portfolio_value: number;
    benchmark_value: number;
  }>;
}

function BacktesterContent() {
  const searchParams = useSearchParams();
  const [nlPrompt, setNlPrompt] = useState("");
  const [isParsing, setIsParsing] = useState(false);
  const [parseSource, setParseSource] = useState<string | null>(null);

  // Form State — pre-fill from URL params (e.g. Clone from leaderboard)
  const [ticker, setTicker] = useState("RELIANCE.NS");

  useEffect(() => {
    const urlTicker = searchParams.get("ticker");
    const urlStrategy = searchParams.get("strategy");
    if (urlTicker) setTicker(urlTicker);
    if (urlStrategy) setNlPrompt(urlStrategy);
  }, [searchParams]);
  const [entryIndicator, setEntryIndicator] = useState("RSI");
  const [entryCondition, setEntryCondition] = useState("crosses_below");
  const [entryValue, setEntryValue] = useState("30");

  const [exitIndicator, setExitIndicator] = useState("RSI");
  const [exitCondition, setExitCondition] = useState("crosses_above");
  const [exitValue, setExitValue] = useState("70");

  const [stopLossPct, setStopLossPct] = useState("5.0");
  const [takeProfitPct, setTakeProfitPct] = useState("15.0");
  const [capital, setCapital] = useState("100000");

  const today = new Date();
  const threeYearsAgo = new Date(today);
  threeYearsAgo.setFullYear(today.getFullYear() - 3);
  const defaultStart = threeYearsAgo.toISOString().split("T")[0];
  const defaultEnd = new Date(today.getFullYear(), today.getMonth(), 0).toISOString().split("T")[0]; // last day of prev month

  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);
  const [scenarioLabel, setScenarioLabel] = useState("Recent 3-Year Performance");

  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<BacktestResults | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resultsRef = useRef<HTMLDivElement>(null);

  const handleExportCSV = () => {
    if (!results || !results.trade_log.length) return;
    const headers = ["Entry Date", "Exit Date", "Entry Price", "Exit Price", "Shares", "P&L (Rs)", "P&L (%)", "Result"];
    const rows = results.trade_log.map(t => [
      t.entry_date, t.exit_date, t.entry_price, t.exit_price, t.shares, t.pnl, t.pnl_pct, t.win ? "WIN" : "LOSS"
    ]);
    const csvContent = [headers, ...rows]
      .map(row => row.map(v => `"${v}"`).join(","))
      .join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${results.ticker}_backtest_trades.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Scenario Presets
  const presets = [
    {
      label: "COVID-19 Crash & Recovery",
      ticker: "RELIANCE.NS",
      start: "2020-02-01",
      end: "2020-08-31",
      desc: "Fast bear crash and sharp V-shaped recovery",
    },
    {
      label: "Global Financial Crisis (GFC)",
      ticker: "TCS.NS",
      start: "2008-01-01",
      end: "2009-03-31",
      desc: "50%+ market drawdown during credit crash",
    },
    {
      label: "2016 Demonetization",
      ticker: "INFY.NS",
      start: "2016-11-01",
      end: "2017-01-31",
      desc: "Short sharp policy shock volatility",
    },
    {
      label: "Ketan Parekh Tech Crash",
      ticker: "WIPRO.NS",
      start: "2000-02-01",
      end: "2001-09-30",
      desc: "Dot-com sector bubble collapse",
    },
    {
      label: "Adani-Hindenburg Shock",
      ticker: "ADANIENT.NS",
      start: "2023-01-15",
      end: "2023-04-30",
      desc: "Concentrated short report volatility",
    },
    {
      label: "Harshad Mehta Scam (1992)",
      ticker: "RELIANCE.NS",
      start: "1992-03-01",
      end: "1992-06-30",
      desc: "⚠️ SENSEX index-level approximation",
    },
  ];

  const handleApplyPreset = (p: typeof presets[0]) => {
    setTicker(p.ticker);
    setStartDate(p.start);
    setEndDate(p.end);
    setScenarioLabel(p.label);
  };

  const handleParseNL = async () => {
    if (!nlPrompt.trim()) return;
    setIsParsing(true);
    setErrorMessage(null);
    setParseSource(null);

    try {
      const data = await api.post<{ status: string; source: string; strategy_json: any }>(
        "/api/backtest/parse",
        { text: nlPrompt.trim() }
      );

      if (data.strategy_json) {
        const s = data.strategy_json;
        setParseSource(data.source === "gemini_ai" ? "Gemini AI" : "Rule Engine");

        if (s.ticker) setTicker(s.ticker);
        if (s.entry_rule) {
          setEntryIndicator(s.entry_rule.indicator || "RSI");
          setEntryCondition(s.entry_rule.condition || "crosses_below");
          setEntryValue(String(s.entry_rule.value || 30));
        }
        if (s.exit_rule) {
          setExitIndicator(s.exit_rule.indicator || "RSI");
          setExitCondition(s.exit_rule.condition || "crosses_above");
          setExitValue(String(s.exit_rule.value || 70));
        }
        if (s.stop_loss_pct) setStopLossPct(String(s.stop_loss_pct));
        if (s.take_profit_pct) setTakeProfitPct(String(s.take_profit_pct));
        if (s.date_range) {
          setStartDate(s.date_range.start || "2020-02-01");
          setEndDate(s.date_range.end || "2020-08-31");
        }
        if (s.scenario_label) setScenarioLabel(s.scenario_label);
      }
    } catch (err: any) {
      setErrorMessage("Could not parse strategy. Please refine prompt or use dropdown builder below.");
    } finally {
      setIsParsing(false);
    }
  };

  const handleRunBacktest = async () => {
    setIsRunning(true);
    setErrorMessage(null);

    const payload = {
      ticker,
      entry_rule: {
        indicator: entryIndicator,
        condition: entryCondition,
        value: parseFloat(entryValue) || 30,
      },
      exit_rule: {
        indicator: exitIndicator,
        condition: exitCondition,
        value: parseFloat(exitValue) || 70,
      },
      position_sizing: { type: "fixed_capital", amount: parseFloat(capital) || 100000 },
      stop_loss_pct: parseFloat(stopLossPct) || 5.0,
      take_profit_pct: parseFloat(takeProfitPct) || 15.0,
      date_range: { start: startDate, end: endDate },
    };

    try {
      const data = await api.post<BacktestResults>("/api/backtest", payload);
      if (data.error) {
        setErrorMessage(data.error);
      } else {
        setResults(data);
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: "smooth" });
        }, 100);
      }
    } catch (err: any) {
      setErrorMessage("Failed to execute backtest simulation. Check parameters.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="border border-border bg-surface rounded-card p-6 relative overflow-hidden">
        <div className="absolute right-4 top-4 opacity-10 pointer-events-none">
          <BrainCircuit className="w-32 h-32 text-secondary" />
        </div>
        <div className="max-w-3xl space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-secondary/10 border border-secondary/20 text-secondary text-xs font-semibold">
            <Zap className="w-3.5 h-3.5" />
            Deterministic Python Engine + Gemini 2.5 Flash Parsing
          </div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-neutralText">
            Natural-Language & Guided Strategy Backtester
          </h1>
          <p className="text-sm text-mutedText leading-relaxed">
            Test trading ideas on historical NSE data. Type your strategy in plain English or configure parameters below. Results run on pure vectorized Python math — zero LLM hallucination.
          </p>
        </div>
      </div>

      {/* Natural Language Prompt Card */}
      <div className="border border-border bg-surface rounded-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-secondary" />
            Describe Strategy in Plain English
          </h3>
          {parseSource && (
            <span className="text-xs px-2.5 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 font-medium">
              Parsed via {parseSource}
            </span>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={nlPrompt}
            onChange={(e) => setNlPrompt(e.target.value)}
            placeholder="e.g., Buy Reliance when RSI drops below 30, sell at RSI 70 with 5% stop loss during COVID crash"
            className="flex-1 bg-bg border border-border rounded-lg px-4 py-2.5 text-sm text-neutralText placeholder-mutedText focus:outline-none focus:border-secondary transition-colors"
          />
          <button
            onClick={handleParseNL}
            disabled={isParsing}
            className="px-5 py-2.5 rounded-lg bg-secondary text-bg font-semibold text-sm hover:bg-secondary/90 transition-colors flex items-center justify-center gap-2 flex-shrink-0 disabled:opacity-50"
          >
            {isParsing ? (
              <>Parsing Prompt...</>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Parse to Form
              </>
            )}
          </button>
        </div>
      </div>

      {/* Scenario Presets Library */}
      <div className="space-y-3">
        <h3 className="font-heading font-semibold text-sm text-neutralText flex items-center gap-2">
          <History className="w-4 h-4 text-primary" />
          Historical Crisis Presets Library
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {presets.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleApplyPreset(p)}
              className="text-left border border-border bg-surface hover:border-primary/50 p-3.5 rounded-lg transition-all group space-y-1"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-neutralText group-hover:text-primary transition-colors">
                  {p.label}
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg text-mutedText">
                  {p.ticker.replace(".NS", "")}
                </span>
              </div>
              <p className="text-[11px] text-mutedText">{p.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Guided Builder Form */}
      <div className="border border-border bg-surface rounded-card p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
            <Sliders className="w-4 h-4 text-primary" />
            Guided Builder Parameters
          </h3>
          <span className="text-xs text-mutedText">Review or edit parsed form fields</span>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-lg bg-negative/10 border border-negative/30 text-negative text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Target Stock */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-mutedText">Target Ticker</label>
            <SearchAutocomplete
              placeholder="Search ticker..."
              onSelect={(selected) => setTicker(selected)}
            />
            <span className="text-[10px] text-primary font-mono font-semibold">Active: {ticker}</span>
          </div>

          {/* Initial Capital */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-mutedText">Capital (₹)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-neutralText focus:outline-none focus:border-primary"
            />
          </div>

          {/* Stop Loss % */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-mutedText">Stop Loss (%)</label>
            <input
              type="number"
              step="0.5"
              value={stopLossPct}
              onChange={(e) => setStopLossPct(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-neutralText focus:outline-none focus:border-primary"
            />
          </div>

          {/* Take Profit % */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-mutedText">Take Profit (%)</label>
            <input
              type="number"
              step="0.5"
              value={takeProfitPct}
              onChange={(e) => setTakeProfitPct(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-neutralText focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        {/* Indicator Rules Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Entry Rule */}
          <div className="border border-border/80 bg-bg/40 p-4 rounded-lg space-y-3">
            <span className="text-xs font-semibold text-positive flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5" /> ENTRY RULE
            </span>
            <div className="grid grid-cols-3 gap-2">
              <select
                value={entryIndicator}
                onChange={(e) => setEntryIndicator(e.target.value)}
                className="bg-surface border border-border rounded px-2 py-1.5 text-xs text-neutralText"
              >
                <option value="RSI">RSI (14)</option>
                <option value="SMA_CROSS">SMA Cross</option>
                <option value="EMA_CROSS">EMA Cross</option>
                <option value="MACD">MACD</option>
                <option value="BOLLINGER">Bollinger</option>
              </select>

              <select
                value={entryCondition}
                onChange={(e) => setEntryCondition(e.target.value)}
                className="bg-surface border border-border rounded px-2 py-1.5 text-xs text-neutralText"
              >
                <option value="crosses_below">Crosses Below</option>
                <option value="crosses_above">Crosses Above</option>
              </select>

              <input
                type="number"
                value={entryValue}
                onChange={(e) => setEntryValue(e.target.value)}
                placeholder="Value"
                className="bg-surface border border-border rounded px-2 py-1.5 text-xs text-neutralText"
              />
            </div>
          </div>

          {/* Exit Rule */}
          <div className="border border-border/80 bg-bg/40 p-4 rounded-lg space-y-3">
            <span className="text-xs font-semibold text-negative flex items-center gap-1.5">
              <TrendingDown className="w-3.5 h-3.5" /> EXIT RULE
            </span>
            <div className="grid grid-cols-3 gap-2">
              <select
                value={exitIndicator}
                onChange={(e) => setExitIndicator(e.target.value)}
                className="bg-surface border border-border rounded px-2 py-1.5 text-xs text-neutralText"
              >
                <option value="RSI">RSI (14)</option>
                <option value="SMA_CROSS">SMA Cross</option>
                <option value="EMA_CROSS">EMA Cross</option>
                <option value="MACD">MACD</option>
                <option value="BOLLINGER">Bollinger</option>
              </select>

              <select
                value={exitCondition}
                onChange={(e) => setExitCondition(e.target.value)}
                className="bg-surface border border-border rounded px-2 py-1.5 text-xs text-neutralText"
              >
                <option value="crosses_above">Crosses Above</option>
                <option value="crosses_below">Crosses Below</option>
              </select>

              <input
                type="number"
                value={exitValue}
                onChange={(e) => setExitValue(e.target.value)}
                placeholder="Value"
                className="bg-surface border border-border rounded px-2 py-1.5 text-xs text-neutralText"
              />
            </div>
          </div>
        </div>

        {/* Date Range & Run CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-border/40">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="space-y-1">
              <span className="text-[10px] text-mutedText block">Start Date</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-bg border border-border rounded px-2.5 py-1 text-xs text-neutralText"
              />
            </div>
            <span className="text-mutedText mt-4">to</span>
            <div className="space-y-1">
              <span className="text-[10px] text-mutedText block">End Date</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="bg-bg border border-border rounded px-2.5 py-1 text-xs text-neutralText"
              />
            </div>
          </div>

          <button
            onClick={handleRunBacktest}
            disabled={isRunning}
            className="w-full sm:w-auto px-8 py-3 rounded-lg bg-primary text-neutralText font-semibold text-sm hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isRunning ? (
              <>Simulating Python Math...</>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                Run Vectorized Simulation
              </>
            )}
          </button>
        </div>
      </div>

      {/* Backtest Results Dashboard */}
      {results && (
        <div ref={resultsRef} className="space-y-6 pt-4 border-t border-border">
          {/* Results Summary Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="border border-border bg-surface p-3.5 rounded-lg text-center">
              <span className="text-[10px] text-mutedText uppercase tracking-wider block">Total Return</span>
              <span className={`font-heading font-bold text-lg ${results.total_return_pct >= 0 ? "text-positive" : "text-negative"}`}>
                {results.total_return_pct >= 0 ? "+" : ""}{results.total_return_pct}%
              </span>
            </div>

            <div className="border border-border bg-surface p-3.5 rounded-lg text-center">
              <span className="text-[10px] text-mutedText uppercase tracking-wider block">CAGR</span>
              <span className={`font-heading font-bold text-lg ${results.cagr >= 0 ? "text-positive" : "text-negative"}`}>
                {results.cagr}%
              </span>
            </div>

            <div className="border border-border bg-surface p-3.5 rounded-lg text-center">
              <span className="text-[10px] text-mutedText uppercase tracking-wider block">Max Drawdown</span>
              <span className="font-heading font-bold text-lg text-negative">
                -{results.max_drawdown_pct}%
              </span>
            </div>

            <div className="border border-border bg-surface p-3.5 rounded-lg text-center">
              <span className="text-[10px] text-mutedText uppercase tracking-wider block">Sharpe Ratio</span>
              <span className="font-heading font-bold text-lg text-secondary">
                {results.sharpe_ratio}
              </span>
            </div>

            <div className="border border-border bg-surface p-3.5 rounded-lg text-center">
              <span className="text-[10px] text-mutedText uppercase tracking-wider block">Win Rate</span>
              <span className="font-heading font-bold text-lg text-neutralText">
                {results.win_rate_pct}%
              </span>
            </div>

            <div className="border border-border bg-surface p-3.5 rounded-lg text-center">
              <span className="text-[10px] text-mutedText uppercase tracking-wider block">Total Trades</span>
              <span className="font-heading font-bold text-lg text-neutralText">
                {results.total_trades}
              </span>
            </div>
          </div>

          {/* Equity Curve Line Chart */}
          <EquityCurveChart data={results.equity_curve} initialCapital={results.initial_capital} />

          {/* Trade Log Table */}
          <div className="border border-border bg-surface rounded-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-heading font-semibold text-sm text-neutralText flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4 text-primary" />
                Detailed Trade Log ({results.trade_log.length} Executed Trades)
              </h4>
              {results.trade_log.length > 0 && (
                <button
                  onClick={handleExportCSV}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-semibold text-mutedText hover:text-primary hover:border-primary/50 transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  Export CSV
                </button>
              )}
            </div>

            {results.trade_log.length === 0 ? (
              <p className="text-xs text-mutedText p-4 text-center">No trades triggered during selected period.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs min-w-[700px]">
                  <thead className="bg-bg text-mutedText border-b border-border">
                    <tr>
                      <th className="p-2.5">Entry Date</th>
                      <th className="p-2.5">Exit Date</th>
                      <th className="p-2.5">Entry (₹)</th>
                      <th className="p-2.5">Exit (₹)</th>
                      <th className="p-2.5">Shares</th>
                      <th className="p-2.5">P&L (₹)</th>
                      <th className="p-2.5">P&L (%)</th>
                      <th className="p-2.5">Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {results.trade_log.map((t, idx) => (
                      <tr key={idx} className="hover:bg-bg/40 transition-colors">
                        <td className="p-2.5 font-mono">{t.entry_date}</td>
                        <td className="p-2.5 font-mono">{t.exit_date}</td>
                        <td className="p-2.5">₹{t.entry_price}</td>
                        <td className="p-2.5">₹{t.exit_price}</td>
                        <td className="p-2.5">{t.shares}</td>
                        <td className={`p-2.5 font-semibold ${t.win ? "text-positive" : "text-negative"}`}>
                          {t.pnl >= 0 ? "+" : ""}₹{t.pnl}
                        </td>
                        <td className={`p-2.5 font-semibold ${t.win ? "text-positive" : "text-negative"}`}>
                          {t.pnl_pct >= 0 ? "+" : ""}{t.pnl_pct}%
                        </td>
                        <td className="p-2.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              t.win ? "bg-positive/20 text-positive" : "bg-negative/20 text-negative"
                            }`}
                          >
                            {t.win ? "WIN" : "LOSS"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function BacktesterPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-mutedText">Loading Backtester Engine...</p>
        </div>
      }
    >
      <BacktesterContent />
    </Suspense>
  );
}
