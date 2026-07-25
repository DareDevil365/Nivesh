"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import GlossaryTooltip from "@/components/GlossaryTooltip";
import SectorHeatmap from "@/components/SectorHeatmap";
import { Filter, Download, Sparkles, RefreshCw, CheckCircle2, TrendingUp } from "lucide-react";

interface StockResult {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  fundamentals: {
    pe: number;
    pb: number;
    roe: number;
    roce: number;
    debt_equity: number;
    div_yield: number;
    revenue_growth_3yr: number;
    eps_growth_3yr: number;
    promoter_holding: number;
    pledged_shares_pct: number;
    market_cap: number;
    current_price: number;
    day_change_pct: number;
  };
  snowflake_scores: {
    value: number;
    future: number;
    past: number;
    health: number;
    dividend: number;
  };
}

const PRESETS = [
  { id: "quality_compounders", name: "Quality Compounders", desc: "ROE > 15%, ROCE > 15%, Low Debt" },
  { id: "deep_value", name: "Deep Value", desc: "Low P/E & P/B, Dividend > 1%" },
  { id: "high_dividend", name: "High Dividend Yield", desc: "Div Yield > 1.5%, High ROE" },
  { id: "low_debt_growth", name: "Low Debt + High Growth", desc: "Debt/Eq < 0.15, Profit Growth > 12%" },
  { id: "zero_pledge", name: "Zero Promoter Pledge", desc: "Zero Pledged Shares, Promoter > 45%" },
  { id: "sector_leaders", name: "Sector Leaders", desc: "Market Cap > ₹50,000 Cr, High ROCE" },
  { id: "garp", name: "GARP Growth", desc: "P/E < 30, Profit Growth > 12%" },
  { id: "cash_flow_kings", name: "Cash Flow Kings", desc: "ROCE > 18%, Low Debt" },
];

export default function ScreenerPage() {
  const [activePreset, setActivePreset] = useState<string>("quality_compounders");
  const [maxPE, setMaxPE] = useState<string>("");
  const [minROE, setMinROE] = useState<string>("");
  const [maxDebtEq, setMaxDebtEq] = useState<string>("");

  const [results, setResults] = useState<StockResult[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchScreenerData = async () => {
    setLoading(true);
    try {
      let queryParams = new URLSearchParams();
      if (activePreset) queryParams.append("preset", activePreset);
      if (maxPE) queryParams.append("max_pe", maxPE);
      if (minROE) queryParams.append("min_roe", minROE);
      if (maxDebtEq) queryParams.append("max_debt_equity", maxDebtEq);

      const res = await fetch(`http://localhost:8000/api/screener?${queryParams.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch (err) {
      console.warn("FastAPI backend starting, using client fallback screener results:", err);
      setResults([
        {
          ticker: "RELIANCE.NS",
          name: "Reliance Industries",
          sector: "Energy & Oil",
          industry: "Refineries",
          fundamentals: { pe: 24.5, pb: 3.2, roe: 16.5, roce: 18.2, debt_equity: 0.35, div_yield: 1.45, revenue_growth_3yr: 14.2, eps_growth_3yr: 16.8, promoter_holding: 50.5, pledged_shares_pct: 0.0, market_cap: 1850000000000, current_price: 2980.5, day_change_pct: 1.25 },
          snowflake_scores: { value: 5, future: 4, past: 4, health: 5, dividend: 5 }
        },
        {
          ticker: "TCS.NS",
          name: "Tata Consultancy Services",
          sector: "Information Technology",
          industry: "IT Software",
          fundamentals: { pe: 28.2, pb: 11.5, roe: 48.5, roce: 55.2, debt_equity: 0.05, div_yield: 1.85, revenue_growth_3yr: 12.5, eps_growth_3yr: 14.1, promoter_holding: 72.3, pledged_shares_pct: 0.0, market_cap: 1420000000000, current_price: 3940.0, day_change_pct: 0.85 },
          snowflake_scores: { value: 4, future: 5, past: 6, health: 6, dividend: 5 }
        },
        {
          ticker: "INFY.NS",
          name: "Infosys Ltd",
          sector: "Information Technology",
          industry: "IT Software",
          fundamentals: { pe: 23.4, pb: 7.8, roe: 31.2, roce: 36.5, debt_equity: 0.08, div_yield: 2.10, revenue_growth_3yr: 11.8, eps_growth_3yr: 12.4, promoter_holding: 14.8, pledged_shares_pct: 0.0, market_cap: 67000000000, current_price: 1620.4, day_change_pct: -0.40 },
          snowflake_scores: { value: 4, future: 4, past: 5, health: 6, dividend: 5 }
        },
        {
          ticker: "HDFCBANK.NS",
          name: "HDFC Bank Ltd",
          sector: "Financial Services",
          industry: "Banking",
          fundamentals: { pe: 18.5, pb: 2.6, roe: 16.8, roce: 17.5, debt_equity: 0.85, div_yield: 1.15, revenue_growth_3yr: 18.5, eps_growth_3yr: 19.2, promoter_holding: 0.0, pledged_shares_pct: 0.0, market_cap: 1100000000000, current_price: 1440.15, day_change_pct: 0.60 },
          snowflake_scores: { value: 5, future: 5, past: 5, health: 4, dividend: 3 }
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScreenerData();
  }, [activePreset]);

  const exportToCSV = () => {
    if (!results || results.length === 0) return;
    const headers = ["Ticker", "Company Name", "Sector", "Price (INR)", "P/E", "P/B", "ROE %", "ROCE %", "Debt/Eq", "Div Yield %"];
    const rows = results.map(r => [
      r.ticker,
      `"${r.name}"`,
      `"${r.sector}"`,
      r.fundamentals.current_price,
      r.fundamentals.pe,
      r.fundamentals.pb,
      r.fundamentals.roe,
      r.fundamentals.roce,
      r.fundamentals.debt_equity,
      r.fundamentals.div_yield
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `nivesh_screener_results_${activePreset}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-surface border border-border rounded-card p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 border border-primary/30 text-positive text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            Screener.in Parity • Dynamic Query Engine
          </div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-neutralText">
            NSE Equity Stock Screener
          </h1>
          <p className="text-mutedText text-xs md:text-sm">
            Filter 2,000+ NSE companies across financial ratios, growth parameters, and valuation metrics.
          </p>
        </div>

        <button
          onClick={exportToCSV}
          className="bg-primary hover:bg-primary/90 text-white font-semibold text-xs px-5 py-3 rounded-lg flex items-center gap-2 shadow transition-colors self-start md:self-auto"
        >
          <Download className="w-4 h-4" />
          Export CSV Results
        </button>
      </div>

      {/* Preset Screen Tabs */}
      <div className="space-y-3">
        <h2 className="font-heading font-semibold text-base text-neutralText">
          Pre-built Preset Screens
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => setActivePreset(p.id)}
              className={`p-3 rounded-lg border text-left flex flex-col justify-between transition-all ${
                activePreset === p.id
                  ? "bg-primary/20 border-primary text-positive"
                  : "bg-surface border-border text-mutedText hover:text-neutralText hover:border-border/80"
              }`}
            >
              <div className="font-heading font-bold text-xs line-clamp-1">{p.name}</div>
              <div className="text-[10px] text-mutedText line-clamp-2 mt-1">{p.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Tijori Sector Heatmap */}
      <SectorHeatmap />

      {/* Screener Results Data Table */}
      <div className="bg-surface border border-border rounded-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-primary" />
            <h3 className="font-heading font-bold text-base text-neutralText">
              Screener Results ({results.length} Stocks)
            </h3>
          </div>
          <span className="text-xs text-mutedText">Hover over column terms for definitions</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-border text-mutedText uppercase text-[11px] font-semibold">
                <th className="py-3 px-4">Company</th>
                <th className="py-3 px-3">Price</th>
                <th className="py-3 px-3"><GlossaryTooltip term="P/E Ratio" /></th>
                <th className="py-3 px-3"><GlossaryTooltip term="P/B Ratio" /></th>
                <th className="py-3 px-3"><GlossaryTooltip term="ROE" /> %</th>
                <th className="py-3 px-3"><GlossaryTooltip term="ROCE" /> %</th>
                <th className="py-3 px-3"><GlossaryTooltip term="Debt / Equity" /></th>
                <th className="py-3 px-3"><GlossaryTooltip term="Dividend Yield" /></th>
                <th className="py-3 px-3"><GlossaryTooltip term="Snowflake" /></th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {results.map((stk) => {
                const totalSnowflake = Object.values(stk.snowflake_scores).reduce((a, b) => a + b, 0);
                return (
                  <tr key={stk.ticker} className="hover:bg-bg/50 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-neutralText">
                      <Link href={`/stock/${stk.ticker}`} className="hover:text-primary transition-colors block">
                        <div>{stk.name}</div>
                        <div className="text-[10px] text-mutedText">{stk.ticker} • {stk.sector}</div>
                      </Link>
                    </td>
                    <td className="py-3.5 px-3 font-semibold text-neutralText">
                      ₹{stk.fundamentals.current_price.toLocaleString("en-IN")}
                    </td>
                    <td className="py-3.5 px-3 text-neutralText">{stk.fundamentals.pe}x</td>
                    <td className="py-3.5 px-3 text-neutralText">{stk.fundamentals.pb}x</td>
                    <td className="py-3.5 px-3 font-semibold text-positive">{stk.fundamentals.roe}%</td>
                    <td className="py-3.5 px-3 font-semibold text-positive">{stk.fundamentals.roce}%</td>
                    <td className="py-3.5 px-3 text-neutralText">{stk.fundamentals.debt_equity}</td>
                    <td className="py-3.5 px-3 text-secondary">{stk.fundamentals.div_yield}%</td>
                    <td className="py-3.5 px-3">
                      <span className="px-2 py-0.5 rounded bg-primary/20 text-positive font-bold text-[11px] border border-primary/30">
                        {totalSnowflake}/30
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/stock/${stk.ticker}`}
                        className="text-xs text-primary hover:underline font-medium"
                      >
                        Analyze →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
