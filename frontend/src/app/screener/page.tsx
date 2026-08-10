"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import GlossaryTooltip from "@/components/GlossaryTooltip";
import SectorHeatmap from "@/components/SectorHeatmap";
import { api } from "@/lib/api";
import {
  Filter,
  Download,
  Sparkles,
  RefreshCw,
  TrendingUp,
  LayoutGrid,
  List,
  ChevronLeft,
  ChevronRight,
  Loader2,
  SlidersHorizontal,
} from "lucide-react";

interface StockResult {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  current_price: number;
  day_change_pct: number;
  market_cap: number;
  pe: number;
  pb: number;
  roe: number;
  roce: number;
  debt_equity: number;
  div_yield: number;
  revenue_growth_3yr: number;
  snowflake_total?: number;
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
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");

  // Custom Filter State
  const [maxPE, setMaxPE] = useState<string>("");
  const [minROE, setMinROE] = useState<string>("");
  const [minROCE, setMinROCE] = useState<string>("");
  const [maxDebtEq, setMaxDebtEq] = useState<string>("");
  const [minDivYield, setMinDivYield] = useState<string>("");
  const [minRevGrowth, setMinRevGrowth] = useState<string>("");
  const [minMarketCapCr, setMinMarketCapCr] = useState<string>("");
  const [selectedSector, setSelectedSector] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("market_cap");

  const [results, setResults] = useState<StockResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [watchlistSaveSuccess, setWatchlistSaveSuccess] = useState(false);

  const handleSaveAllToWatchlist = async () => {
    if (!results || results.length === 0) return;
    try {
      for (const stock of results.slice(0, 15)) {
        await api.post("/api/watchlist/item", {
          watchlist_name: "default",
          ticker: stock.ticker,
        });
      }
      setWatchlistSaveSuccess(true);
      setTimeout(() => setWatchlistSaveSuccess(false), 2500);
    } catch (err) {
      console.warn("Failed to save to watchlist:", err);
    }
  };

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const fetchScreenerData = async (useCustom: boolean = false) => {
    setLoading(true);
    setCurrentPage(1);
    try {
      let queryParams = new URLSearchParams();

      if (!useCustom && activePreset) {
        queryParams.append("preset", activePreset);
      }

      if (useCustom) {
        if (maxPE) queryParams.append("max_pe", maxPE);
        if (minROE) queryParams.append("min_roe", minROE);
        if (minROCE) queryParams.append("min_roce", minROCE);
        if (maxDebtEq) queryParams.append("max_debt_equity", maxDebtEq);
        if (minDivYield) queryParams.append("min_div_yield", minDivYield);
        if (minRevGrowth) queryParams.append("min_revenue_growth", minRevGrowth);
        if (minMarketCapCr)
          queryParams.append("min_market_cap", String(parseFloat(minMarketCapCr) * 10000000));
        if (selectedSector) queryParams.append("sector", selectedSector);
      }

      if (sortBy) queryParams.append("sort_by", sortBy);

      const data = await api.get<{ results: StockResult[] }>(`/api/screener?${queryParams.toString()}`);
      setResults(data.results || []);
    } catch (err) {
      console.warn("Screener fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScreenerData(isCustomMode);
  }, [activePreset, sortBy]);

  const handleSelectPreset = (presetId: string) => {
    setIsCustomMode(false);
    setActivePreset(presetId);
  };

  const handleApplyCustomFilter = (e: React.FormEvent) => {
    e.preventDefault();
    setIsCustomMode(true);
    fetchScreenerData(true);
  };

  const handleClearCustom = () => {
    setMaxPE("");
    setMinROE("");
    setMinROCE("");
    setMaxDebtEq("");
    setMinDivYield("");
    setMinRevGrowth("");
    setMinMarketCapCr("");
    setSelectedSector("");
    setIsCustomMode(false);
    setActivePreset("quality_compounders");
  };

  const handleExportCSV = () => {
    if (!results || results.length === 0) return;

    const headers = [
      "Ticker",
      "Company Name",
      "Sector",
      "Price (INR)",
      "P/E",
      "P/B",
      "ROE (%)",
      "ROCE (%)",
      "Debt/Equity",
      "Div Yield (%)",
      "Market Cap (Cr)",
    ];

    const rows = results.map((r) => [
      r.ticker,
      `"${r.name}"`,
      `"${r.sector}"`,
      r.current_price,
      r.pe,
      r.pb,
      r.roe,
      r.roce,
      r.debt_equity,
      r.div_yield,
      (r.market_cap / 10000000).toFixed(2),
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Nivesh_Screener_${activePreset || "Custom"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Pagination calculation
  const totalPages = Math.ceil(results.length / pageSize) || 1;
  const paginatedResults = results.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="border border-border bg-surface rounded-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 text-xs text-primary font-semibold">
            <Filter className="w-3.5 h-3.5" />
            Nifty 500 Equity Screener
          </div>
          <h1 className="font-heading text-2xl font-bold text-neutralText">
            NSE Stock Screener & Filter Engine
          </h1>
          <p className="text-sm text-mutedText max-w-2xl">
            Screen top Indian equities using pre-built financial strategies or construct custom multi-metric ratio queries.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            disabled={results.length === 0}
            className="px-4 py-2 rounded-lg bg-surface border border-border hover:border-primary text-xs font-semibold text-neutralText transition-colors flex items-center gap-2 disabled:opacity-40"
          >
            <Download className="w-3.5 h-3.5 text-primary" />
            Export CSV ({results.length})
          </button>
        </div>
      </div>

      {/* Preset Screen Quick Buttons */}
      <div className="space-y-3">
        <h3 className="font-heading font-semibold text-xs text-mutedText uppercase tracking-wider">
          Pre-Built Strategy Screens
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {PRESETS.map((p) => {
            const isActive = !isCustomMode && activePreset === p.id;
            return (
              <button
                key={p.id}
                onClick={() => handleSelectPreset(p.id)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  isActive
                    ? "bg-primary/20 border-primary text-neutralText shadow-sm"
                    : "bg-surface border-border hover:border-primary/50 text-mutedText hover:text-neutralText"
                }`}
              >
                <span className="font-heading font-bold text-xs block truncate">{p.name}</span>
                <span className="text-[10px] text-mutedText/80 block line-clamp-1 mt-0.5">{p.desc}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Custom Query Builder Panel */}
      <div className="border border-border bg-surface rounded-card p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <h3 className="font-heading font-semibold text-sm text-neutralText flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-primary" />
            Custom Ratio Filter Builder
          </h3>
          {isCustomMode && (
            <span className="text-xs px-2.5 py-0.5 rounded bg-primary/20 text-primary border border-primary/30 font-medium">
              Custom Filter Active
            </span>
          )}
        </div>

        <form onSubmit={handleApplyCustomFilter} className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] text-mutedText">Max P/E Multiple</label>
              <input
                type="number"
                placeholder="e.g. 25"
                value={maxPE}
                onChange={(e) => setMaxPE(e.target.value)}
                className="w-full bg-bg border border-border rounded px-2.5 py-1.5 text-xs text-neutralText"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-mutedText">Min ROE (%)</label>
              <input
                type="number"
                placeholder="e.g. 15"
                value={minROE}
                onChange={(e) => setMinROE(e.target.value)}
                className="w-full bg-bg border border-border rounded px-2.5 py-1.5 text-xs text-neutralText"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-mutedText">Min ROCE (%)</label>
              <input
                type="number"
                placeholder="e.g. 15"
                value={minROCE}
                onChange={(e) => setMinROCE(e.target.value)}
                className="w-full bg-bg border border-border rounded px-2.5 py-1.5 text-xs text-neutralText"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-mutedText">Max Debt / Eq</label>
              <input
                type="number"
                step="0.1"
                placeholder="e.g. 0.5"
                value={maxDebtEq}
                onChange={(e) => setMaxDebtEq(e.target.value)}
                className="w-full bg-bg border border-border rounded px-2.5 py-1.5 text-xs text-neutralText"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-mutedText">Min Div Yield (%)</label>
              <input
                type="number"
                step="0.5"
                placeholder="e.g. 1.5"
                value={minDivYield}
                onChange={(e) => setMinDivYield(e.target.value)}
                className="w-full bg-bg border border-border rounded px-2.5 py-1.5 text-xs text-neutralText"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-mutedText">Min Rev Growth (%)</label>
              <input
                type="number"
                placeholder="e.g. 10"
                value={minRevGrowth}
                onChange={(e) => setMinRevGrowth(e.target.value)}
                className="w-full bg-bg border border-border rounded px-2.5 py-1.5 text-xs text-neutralText"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-mutedText">Min Mkt Cap (₹ Cr)</label>
              <input
                type="number"
                placeholder="e.g. 5000"
                value={minMarketCapCr}
                onChange={(e) => setMinMarketCapCr(e.target.value)}
                className="w-full bg-bg border border-border rounded px-2.5 py-1.5 text-xs text-neutralText"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/40">
            <button
              type="button"
              onClick={handleClearCustom}
              className="px-3 py-1.5 rounded text-xs text-mutedText hover:text-neutralText transition-colors"
            >
              Reset Filters
            </button>
            <button
              type="submit"
              className="px-5 py-1.5 rounded bg-primary text-neutralText font-semibold text-xs hover:bg-primary/90 transition-colors flex items-center gap-1.5"
            >
              <Filter className="w-3.5 h-3.5" />
              Apply Custom Query
            </button>
          </div>
        </form>
      </div>

      {/* Sector Heatmap Section */}
      <SectorHeatmap />

      {/* Results Header, Sorting & View Toggle Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <h3 className="font-heading font-bold text-lg text-neutralText">
            Screening Results ({results.length} Stocks)
          </h3>
          {loading && <Loader2 className="w-4 h-4 text-primary animate-spin" />}
        </div>

        <div className="flex items-center gap-3">
          {/* Sort By Dropdown */}
          <div className="flex items-center gap-1 text-xs text-mutedText">
            <span>Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-surface border border-border rounded px-2.5 py-1 text-xs text-neutralText"
            >
              <option value="market_cap">Market Cap</option>
              <option value="pe">P/E Ratio</option>
              <option value="roe">ROE %</option>
              <option value="roce">ROCE %</option>
              <option value="snowflake_total">Snowflake Score</option>
            </select>
          </div>

          {/* Action Buttons */}
          <button
            onClick={handleSaveAllToWatchlist}
            disabled={results.length === 0}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-surface border border-border hover:border-primary/50 text-neutralText font-medium text-xs transition-colors disabled:opacity-50"
            title="Add top screening results to your watchlist"
          >
            <Sparkles className="w-3.5 h-3.5 text-positive" />
            {watchlistSaveSuccess ? (
              <span className="text-positive font-semibold">Saved to Watchlist!</span>
            ) : (
              "Save to Watchlist"
            )}
          </button>

          <button
            onClick={handleExportCSV}
            disabled={results.length === 0}
            className="flex items-center gap-1.5 px-3 py-1 rounded bg-surface border border-border hover:border-primary/50 text-neutralText font-medium text-xs transition-colors disabled:opacity-50"
            title="Export screening results as CSV"
          >
            <Download className="w-3.5 h-3.5 text-primary" />
            Export CSV
          </button>

          {/* View Toggle */}
          <div className="flex items-center bg-surface border border-border rounded-lg p-0.5">
            <button
              onClick={() => setViewMode("table")}
              className={`p-1.5 rounded ${
                viewMode === "table" ? "bg-primary text-neutralText" : "text-mutedText hover:text-neutralText"
              }`}
              title="Table View"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded ${
                viewMode === "grid" ? "bg-primary text-neutralText" : "text-mutedText hover:text-neutralText"
              }`}
              title="Grid View"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Results Data View */}
      {loading ? (
        <div className="w-full h-64 border border-border bg-surface rounded-card flex items-center justify-center text-mutedText text-sm gap-2">
          <Loader2 className="w-5 h-5 text-primary animate-spin" />
          <span>Fetching NSE screening candidates...</span>
        </div>
      ) : paginatedResults.length === 0 ? (
        <div className="w-full p-12 border border-border bg-surface rounded-card text-center space-y-2">
          <p className="text-sm font-semibold text-neutralText">No stocks match your filter criteria.</p>
          <p className="text-xs text-mutedText">Try relaxing P/E, debt, or market cap thresholds above.</p>
        </div>
      ) : viewMode === "table" ? (
        /* TABLE VIEW */
        <div className="border border-border bg-surface rounded-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[750px]">
              <thead className="bg-bg text-mutedText border-b border-border">
                <tr>
                  <th className="p-3">Company Ticker</th>
                  <th className="p-3 text-right">Price (₹)</th>
                  <th className="p-3 text-right">
                    <GlossaryTooltip term="P/E Ratio">P/E</GlossaryTooltip>
                  </th>
                  <th className="p-3 text-right">
                    <GlossaryTooltip term="P/B Ratio">P/B</GlossaryTooltip>
                  </th>
                  <th className="p-3 text-right">
                    <GlossaryTooltip term="ROE">ROE (%)</GlossaryTooltip>
                  </th>
                  <th className="p-3 text-right">
                    <GlossaryTooltip term="ROCE">ROCE (%)</GlossaryTooltip>
                  </th>
                  <th className="p-3 text-right">
                    <GlossaryTooltip term="Debt / Equity">D/E</GlossaryTooltip>
                  </th>
                  <th className="p-3 text-right">
                    <GlossaryTooltip term="Dividend Yield">Div Yield (%)</GlossaryTooltip>
                  </th>
                  <th className="p-3 text-right">Mkt Cap (₹ Cr)</th>
                  <th className="p-3 text-right">Snowflake</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {paginatedResults.map((r) => (
                  <tr key={r.ticker} className="hover:bg-bg/40 transition-colors">
                    <td className="p-3">
                      <Link href={`/stock/${r.ticker}`} className="group">
                        <span className="font-semibold text-neutralText group-hover:text-primary transition-colors font-mono">
                          {r.ticker.replace(".NS", "")}
                        </span>
                        <span className="text-[11px] text-mutedText block truncate max-w-[180px]">
                          {r.name}
                        </span>
                      </Link>
                    </td>
                    <td className="p-3 text-right font-mono">₹{r.current_price}</td>
                    <td className="p-3 text-right font-mono">{r.pe}x</td>
                    <td className="p-3 text-right font-mono">{r.pb}x</td>
                    <td className="p-3 text-right font-mono text-positive font-semibold">{r.roe}%</td>
                    <td className="p-3 text-right font-mono text-positive font-semibold">{r.roce}%</td>
                    <td className="p-3 text-right font-mono">{r.debt_equity}</td>
                    <td className="p-3 text-right font-mono">{r.div_yield}%</td>
                    <td className="p-3 text-right font-mono">
                      ₹{(r.market_cap / 10000000).toFixed(0)} Cr
                    </td>
                    <td className="p-3 text-right">
                      <span className="inline-flex items-center px-2 py-0.5 rounded bg-bg border border-border text-secondary font-bold font-mono">
                        {r.snowflake_total != null ? `${r.snowflake_total}/30` : "N/A"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* GRID CARD VIEW */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {paginatedResults.map((r) => (
            <Link
              key={r.ticker}
              href={`/stock/${r.ticker}`}
              className="border border-border bg-surface hover:border-primary/50 p-5 rounded-card space-y-3 transition-all group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-heading font-bold text-sm text-neutralText group-hover:text-primary transition-colors">
                    {r.name}
                  </h4>
                  <span className="text-xs font-mono text-mutedText">{r.ticker}</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-secondary/10 text-secondary border border-secondary/20 text-xs font-bold font-mono">
                  {r.snowflake_total != null ? `${r.snowflake_total}/30` : "N/A"}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border/40 text-center text-xs">
                <div>
                  <span className="text-[10px] text-mutedText block">P/E</span>
                  <span className="font-mono text-neutralText">{r.pe}x</span>
                </div>
                <div>
                  <span className="text-[10px] text-mutedText block">ROE</span>
                  <span className="font-mono text-positive font-semibold">{r.roe}%</span>
                </div>
                <div>
                  <span className="text-[10px] text-mutedText block">ROCE</span>
                  <span className="font-mono text-positive font-semibold">{r.roce}%</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-border pt-4 text-xs text-mutedText">
          <span>
            Showing page <strong className="text-neutralText">{currentPage}</strong> of {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded border border-border bg-surface hover:bg-bg disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded border border-border bg-surface hover:bg-bg disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
