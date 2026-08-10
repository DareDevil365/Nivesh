"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import SnowflakeChart from "@/components/SnowflakeChart";
import StockChart from "@/components/StockChart";
import DCFCalculator from "@/components/DCFCalculator";
import ResearchDigestCard from "@/components/ResearchDigestCard";
import GlossaryTooltip from "@/components/GlossaryTooltip";
import { FinancialStatements } from "@/components/FinancialStatements";
import { ShareholdingChart } from "@/components/ShareholdingChart";
import { PeerComparison } from "@/components/PeerComparison";
import QuarterlyResults from "@/components/QuarterlyResults";
import RatioTrends from "@/components/RatioTrends";
import GrowthForecastChart from "@/components/GrowthForecastChart";
import ForensicRiskCard from "@/components/ForensicRiskCard";
import ValuationBandsChart from "@/components/ValuationBandsChart";
import ReverseDCFCard from "@/components/ReverseDCFCard";
import RelativeStrengthCard from "@/components/RelativeStrengthCard";
import SupplyChainGraph from "@/components/SupplyChainGraph";
import {
  CheckCircle2, XCircle, Clock, TrendingUp, TrendingDown,
  FileText, AlertCircle, Share2, Globe, Building2,
  ArrowUpRight, ArrowDownRight, ChevronDown, ChevronUp, Info,
  BookmarkPlus, BookmarkCheck,
} from "lucide-react";

interface CompanyProfile {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  isin: string;
  website: string;
  about: string;
  fundamentals: {
    pe: number | null;
    pb: number | null;
    eps: number | null;
    book_value: number | null;
    face_value: number | null;
    week_high_52: number | null;
    week_low_52: number | null;
    roe: number | null;
    roce: number | null;
    debt_equity: number | null;
    div_yield: number;
    payout_ratio: number | null;
    current_ratio: number | null;
    interest_coverage: number | null;
    revenue_growth_3yr: number | null;
    eps_growth_3yr: number | null;
    promoter_holding: number | null;
    pledged_shares_pct: number;
    market_cap: number;
    market_cap_cr: number;
    current_price: number;
    day_change: number;
    day_change_pct: number;
  };
  snowflake_scores: {
    value: number;
    future: number;
    past: number;
    health: number;
    dividend: number;
  };
  pros_cons: {
    pros: Array<{ text: string; rule_id: string }>;
    cons: Array<{ text: string; rule_id: string }>;
  };
  delayed_badge: boolean;
}

// ── Ratio tile helper ──────────────────────────────────────────
function RatioTile({
  label, value, colorClass = "text-neutralText", subtitle,
}: { label: string; value: string; colorClass?: string; subtitle?: string }) {
  return (
    <div className="bg-surface border border-border rounded-card p-3.5 space-y-0.5 hover:border-primary/30 transition-colors">
      <div className="text-[10px] uppercase font-semibold text-mutedText tracking-wide">{label}</div>
      <div className={`font-heading font-bold text-base ${colorClass}`}>{value}</div>
      {subtitle && <div className="text-[9px] text-mutedText">{subtitle}</div>}
    </div>
  );
}

function fmtNum(val: number | null | undefined, suffix = ""): string {
  if (val == null) return "N/A";
  return `${val.toLocaleString("en-IN")}${suffix}`;
}

function fmtCrore(cr: number): string {
  if (cr >= 100_000) return `₹${(cr / 100_000).toFixed(2)}L Cr`;
  if (cr >= 1_000) return `₹${(cr / 1_000).toFixed(1)}K Cr`;
  return `₹${cr.toLocaleString("en-IN")} Cr`;
}

// ──────────────────────────────────────────────────────────────
export default function StockDashboardPage() {
  const params = useParams();
  const rawTicker = (params?.ticker as string) || "RELIANCE.NS";
  const ticker = decodeURIComponent(rawTicker).toUpperCase().trim();

  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);
  const [memoExportSuccess, setMemoExportSuccess] = useState(false);
  const [watchlistSuccess, setWatchlistSuccess] = useState(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [aboutExpanded, setAboutExpanded] = useState(false);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setErrorMsg(null);
      try {
        const profileData = await api.get<CompanyProfile>(
          `/api/companies/${encodeURIComponent(ticker)}`
        );
        setCompany(profileData);
      } catch (err: any) {
        setErrorMsg(err.message || `Unable to fetch live market data for ${ticker}`);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [ticker]);

  const getScoreColor = (score: number) => {
    if (score >= 5) return "text-positive";
    if (score >= 3) return "text-secondary";
    return "text-negative";
  };

  const handleShareReportCard = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  const handleAddToWatchlist = async () => {
    try {
      await api.post("/api/watchlist/item", {
        watchlist_name: "default",
        ticker,
      });
      setWatchlistSuccess(true);
      setTimeout(() => setWatchlistSuccess(false), 2500);
    } catch (err) {
      // Silently fail — watchlist may be unavailable
      console.warn("Watchlist add failed", err);
    }
  };

  const handleExportMemo = () => {
    if (!company || typeof window === "undefined") return;
    const f = company.fundamentals;
    const s = company.snowflake_scores;
    const p = company.pros_cons;

    const memoContent = `# Institutional Equity Investment Memo: ${company.name} (${ticker})
*Generated via Nivesh Quantitative Research Platform — ${new Date().toLocaleDateString("en-IN")}*

## 1. Executive Summary & Market Snapshot
- **Symbol:** ${ticker} (NSE)
- **Sector / Industry:** ${company.sector} | ${company.industry}
- **Current Price:** ₹${f.current_price.toLocaleString("en-IN")} (${f.day_change >= 0 ? "+" : ""}${f.day_change_pct.toFixed(2)}%)
- **Market Capitalization:** ${fmtCrore(f.market_cap_cr)}
- **52-Week Range:** ₹${fmtNum(f.week_low_52)} – ₹${fmtNum(f.week_high_52)}

---

## 2. 5-Axis Snowflake Radar Scores (0-6 Scale)
- **Value Score:** ${s.value}/6 (${s.value >= 4 ? "Attractive Fair Value" : "Premium / Rich Valuation"})
- **Future Growth Score:** ${s.future}/6 (${s.future >= 4 ? "High Revenue/Earnings Growth" : "Moderate Forecast CAGR"})
- **Past Track Record:** ${s.past}/6 (${s.past >= 4 ? "Consistent EPS & Profit Growth" : "Mixed Historical Track Record"})
- **Financial Health:** ${s.health}/6 (${s.health >= 4 ? "Low Debt & High Solvency" : "Leveraged Balance Sheet"})
- **Dividend Payout:** ${s.dividend}/6 (${s.dividend >= 4 ? "Strong & Sustainable Yield" : "Low Payout Ratio"})

---

## 3. Key Financial Ratios & Valuation Summary
- **P/E Ratio:** ${fmtNum(f.pe)}x
- **P/B Ratio:** ${fmtNum(f.pb)}x
- **Return on Equity (ROE):** ${fmtNum(f.roe, "%")}
- **Return on Capital Employed (ROCE):** ${fmtNum(f.roce, "%")}
- **Debt to Equity Ratio:** ${fmtNum(f.debt_equity)}
- **Dividend Yield:** ${fmtNum(f.div_yield, "%")}
- **Promoter Holding:** ${fmtNum(f.promoter_holding, "%")} (${fmtNum(f.pledged_shares_pct, "%")} Pledged)

---

## 4. Rule-Based Strengths & Caution Flags
### Strengths (Pros)
${p.pros.map((item) => `- ✅ ${item.text}`).join("\n") || "- No positive rule flags triggered."}

### Caution Flags (Cons)
${p.cons.map((item) => `- ⚠️ ${item.text}`).join("\n") || "- No negative rule flags triggered."}

---

## 5. Summary Conclusion & Research Notes
${company.name} demonstrates a **${s.health >= 4 ? "strong balance sheet" : "leveraged financial structure"}** with a total Snowflake rating of **${s.value + s.future + s.past + s.health + s.dividend}/30**. 
Investors are advised to review the forensic risk metrics, PE/PB valuation bands, and quarterly revenue trends before position allocation.

---
*Disclaimer: Generated automatically by Nivesh. For educational & research purposes only. Not investment advice.*
`;

    // 1. Copy to clipboard
    navigator.clipboard.writeText(memoContent);
    setMemoExportSuccess(true);
    setTimeout(() => setMemoExportSuccess(false), 2500);

    // 2. Trigger .md download
    const blob = new Blob([memoContent], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Nivesh_Memo_${ticker.replace(".NS", "").replace(".BO", "")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-mutedText text-sm font-medium">Fetching stock data for {ticker}...</p>
      </div>
    );
  }

  if (errorMsg || !company) {
    return (
      <div className="bg-surface border border-red-500/30 rounded-card p-8 text-center space-y-4 max-w-2xl mx-auto my-12">
        <div className="w-12 h-12 rounded-full bg-red-500/20 text-negative flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-heading font-bold text-xl text-neutralText">
          Unable to Fetch Market Data for "{ticker}"
        </h2>
        <p className="text-xs text-mutedText leading-relaxed">
          {errorMsg || "The symbol may be invalid on the National Stock Exchange (NSE) or real-time data is currently unavailable."}
        </p>
        <p className="text-xs text-mutedText">
          Try common NSE symbols like{" "}
          {["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"].map((t) => (
            <a key={t} href={`/stock/${t}`} className="text-primary hover:underline mx-1">{t}</a>
          ))}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-primary hover:bg-primary/90 text-white font-semibold text-xs px-5 py-2.5 rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  const { fundamentals, snowflake_scores, pros_cons } = company;
  const isPositive = fundamentals.day_change >= 0;

  const TABS = [
    { id: "overview", label: "Overview" },
    { id: "growth", label: "Growth & Forecasts" },
    { id: "financials", label: "Financials" },
    { id: "quarterly", label: "Quarterly" },
    { id: "ratios", label: "Key Ratios" },
    { id: "valuation", label: "Valuation" },
    { id: "supply-chain", label: "Supply Chain" },
    { id: "forensic", label: "Forensic Risk" },
    { id: "shareholding", label: "Shareholding" },
    { id: "research", label: "Research Digest" },
  ];

  return (
    <div className="space-y-5">

      {/* ── TOP HEADER CARD ──────────────────────────────── */}
      <div className="bg-surface border border-border rounded-card p-5">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          {/* Left: Name + meta */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="font-heading font-bold text-2xl md:text-3xl text-neutralText">
                {company.name}
              </h1>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-bg text-mutedText border border-border">
                {ticker.replace(".NS", "").replace(".BO", "")}
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                NSE
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-mutedText">
              <span className="flex items-center gap-1">
                <Building2 className="w-3 h-3" />
                {company.sector}
              </span>
              <span className="text-border">·</span>
              <span>{company.industry}</span>
              {company.isin && (
                <>
                  <span className="text-border">·</span>
                  <span className="font-mono">{company.isin}</span>
                </>
              )}
              {company.website && (
                <>
                  <span className="text-border">·</span>
                  <a
                    href={company.website}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline flex items-center gap-0.5"
                  >
                    <Globe className="w-3 h-3" /> Website
                  </a>
                </>
              )}
            </div>

            {/* About — expandable */}
            {company.about && (
              <div className="mt-2 text-xs text-mutedText leading-relaxed max-w-2xl">
                <p className={aboutExpanded ? "" : "line-clamp-2"}>
                  {company.about}
                </p>
                {company.about.length > 200 && (
                  <button
                    onClick={() => setAboutExpanded((x) => !x)}
                    className="text-primary hover:underline flex items-center gap-0.5 mt-0.5 font-medium"
                  >
                    {aboutExpanded ? (
                      <><ChevronUp className="w-3 h-3" /> Show less</>
                    ) : (
                      <><ChevronDown className="w-3 h-3" /> Read more</>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Right: Price + actions */}
          <div className="flex flex-col items-start md:items-end gap-2 shrink-0">
            <div className="flex items-baseline gap-2">
              <span className="font-heading font-bold text-3xl text-neutralText">
                ₹{fundamentals.current_price.toLocaleString("en-IN")}
              </span>
              <span
                className={`inline-flex items-center gap-0.5 font-semibold text-sm px-2 py-0.5 rounded ${
                  isPositive ? "bg-positive/10 text-positive" : "bg-negative/10 text-negative"
                }`}
              >
                {isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                {isPositive ? "+" : ""}
                {fundamentals.day_change} ({isPositive ? "+" : ""}
                {fundamentals.day_change_pct}%)
              </span>
            </div>

            {/* Market Cap */}
            {fundamentals.market_cap_cr > 0 && (
              <div className="text-xs text-mutedText">
                Mkt Cap: <span className="text-neutralText font-semibold">{fmtCrore(fundamentals.market_cap_cr)}</span>
              </div>
            )}

            {/* 52-Week Range Progress Bar */}
            {fundamentals.week_low_52 && fundamentals.week_high_52 && fundamentals.current_price > 0 && (
              <div className="w-full max-w-xs space-y-1">
                <div className="flex justify-between text-[10px] text-mutedText">
                  <span>52W Low ₹{fundamentals.week_low_52}</span>
                  <span>52W High ₹{fundamentals.week_high_52}</span>
                </div>
                <div className="relative h-1.5 bg-bg rounded-full border border-border/60 overflow-hidden">
                  <div
                    className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-negative via-secondary to-positive"
                    style={{
                      width: `${Math.min(100, Math.max(0,
                        ((fundamentals.current_price - fundamentals.week_low_52) /
                        (fundamentals.week_high_52 - fundamentals.week_low_52)) * 100
                      ))}%`
                    }}
                  />
                </div>
                <div className="text-[10px] text-mutedText text-center">
                  {(((fundamentals.current_price - fundamentals.week_low_52) / (fundamentals.week_high_52 - fundamentals.week_low_52)) * 100).toFixed(0)}% from 52W low
                </div>
              </div>
            )}

            <div className="flex items-center gap-2 flex-wrap justify-end">
              <button
                onClick={handleAddToWatchlist}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg border text-xs font-semibold transition-all ${
                  watchlistSuccess
                    ? "bg-positive/20 border-positive/40 text-positive"
                    : "bg-bg border-border text-mutedText hover:border-primary/50 hover:text-primary"
                }`}
                title="Add to Watchlist"
              >
                {watchlistSuccess ? <BookmarkCheck className="w-3.5 h-3.5" /> : <BookmarkPlus className="w-3.5 h-3.5" />}
                {watchlistSuccess ? "Added!" : "Watchlist"}
              </button>

              <button
                onClick={handleExportMemo}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-primary/10 border border-primary/30 text-positive hover:bg-primary/20 transition-all text-xs font-semibold"
                title="Download 1-Click Institutional Markdown Research Memo for Notion / Obsidian"
              >
                <FileText className="w-3.5 h-3.5" />
                {memoExportSuccess ? (
                  <span className="text-positive font-bold">Memo Exported!</span>
                ) : (
                  "Export Memo (.md)"
                )}
              </button>

              <button
                onClick={handleShareReportCard}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border text-mutedText hover:text-neutralText hover:border-primary/50 transition-all text-xs relative"
              >
                <Share2 className="w-3.5 h-3.5" />
                {copySuccess ? (
                  <span className="text-positive font-semibold">Link Copied!</span>
                ) : (
                  "Share"
                )}
              </button>

              <span className="inline-flex items-center gap-1 text-xs text-mutedText bg-bg px-2.5 py-1 rounded-full border border-border">
                <Clock className="w-3.5 h-3.5 text-secondary" /> ~15 min delay
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── KEY RATIOS GRID (expanded) ────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-2.5">
        <RatioTile label="P/E Ratio" value={fundamentals.pe != null ? `${fundamentals.pe}x` : "N/A"} />
        <RatioTile label="P/B Ratio" value={fundamentals.pb != null ? `${fundamentals.pb}x` : "N/A"} />
        <RatioTile label="EPS" value={fundamentals.eps != null ? `₹${fundamentals.eps}` : "N/A"} />
        <RatioTile label="Book Value" value={fundamentals.book_value != null ? `₹${fundamentals.book_value}` : "N/A"} />
        <RatioTile label="Face Value" value={fundamentals.face_value != null ? `₹${fundamentals.face_value}` : "₹10"} />
        <RatioTile
          label="52W High / Low"
          value={
            fundamentals.week_high_52 && fundamentals.week_low_52
              ? `₹${fundamentals.week_high_52} / ₹${fundamentals.week_low_52}`
              : "N/A"
          }
          subtitle={
            fundamentals.week_high_52 && fundamentals.current_price
              ? `${(((fundamentals.current_price - fundamentals.week_high_52) / fundamentals.week_high_52) * 100).toFixed(1)}% from high`
              : undefined
          }
        />
        <RatioTile label="ROE" value={fundamentals.roe != null ? `${fundamentals.roe}%` : "N/A"}
          colorClass={fundamentals.roe != null ? (fundamentals.roe > 15 ? "text-positive" : fundamentals.roe < 8 ? "text-negative" : "text-neutralText") : "text-mutedText"} />
        <RatioTile label="ROCE" value={fundamentals.roce != null ? `${fundamentals.roce}%` : "N/A"}
          colorClass={fundamentals.roce != null ? (fundamentals.roce > 15 ? "text-positive" : fundamentals.roce < 8 ? "text-negative" : "text-neutralText") : "text-mutedText"} />
        <RatioTile label="Debt / Equity"
          value={fundamentals.debt_equity != null ? `${fundamentals.debt_equity}x` : "N/A"}
          colorClass={fundamentals.debt_equity != null ? (fundamentals.debt_equity < 0.5 ? "text-positive" : fundamentals.debt_equity > 1.5 ? "text-negative" : "text-neutralText") : "text-mutedText"} />
        <RatioTile label="Div Yield" value={`${fundamentals.div_yield ?? 0}%`}
          colorClass={fundamentals.div_yield > 3 ? "text-positive" : "text-neutralText"} />
        <RatioTile label="Current Ratio"
          value={fundamentals.current_ratio != null ? `${fundamentals.current_ratio}x` : "N/A"}
          colorClass={fundamentals.current_ratio != null ? (fundamentals.current_ratio > 1.5 ? "text-positive" : fundamentals.current_ratio < 1.0 ? "text-negative" : "text-neutralText") : "text-mutedText"} />
        <RatioTile label="Promoter %" value={fundamentals.promoter_holding != null ? `${fundamentals.promoter_holding}%` : "N/A"}
          colorClass={fundamentals.promoter_holding != null ? (fundamentals.promoter_holding > 50 ? "text-positive" : "text-neutralText") : "text-mutedText"} />
      </div>

      {/* ── SNOWFLAKE + CHART ─────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Snowflake */}
        <div className="bg-surface border border-border rounded-card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-heading font-bold text-base text-neutralText flex items-center gap-1.5">
                <GlossaryTooltip term="Snowflake">Snowflake Analysis</GlossaryTooltip>
              </h2>
              <span className="text-xs text-mutedText">5-Axis Radar</span>
            </div>
            <p className="text-xs text-mutedText mb-4">
              Visual evaluation across Value, Future, Past, Health, and Dividend pillars.
            </p>
          </div>
          <SnowflakeChart scores={snowflake_scores} />
          <div className="grid grid-cols-5 gap-1 text-center mt-4 pt-4 border-t border-border text-[11px]">
            {(["value", "future", "past", "health", "dividend"] as const).map((k) => {
              const LABELS: Record<string, string> = {
                value: "Value", future: "Future", past: "Past", health: "Health", dividend: "Divid."
              };
              return (
                <div key={k}>
                  <div className="text-mutedText uppercase text-[9px]">{LABELS[k]}</div>
                  <div className={`font-bold ${getScoreColor(snowflake_scores[k])}`}>
                    {snowflake_scores[k]}/6
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chart */}
        <div className="lg:col-span-2 bg-surface border border-border rounded-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-bold text-base text-neutralText">Price Chart</h2>
            <span className="text-xs px-2.5 py-1 rounded bg-primary/20 text-positive border border-primary/30 font-semibold">
              Daily OHLCV
            </span>
          </div>
          <StockChart ticker={company.ticker} />
        </div>
      </div>



      {/* ── TAB NAVIGATION ───────────────────────────────── */}
      <div className="bg-surface border border-border rounded-card overflow-hidden">
        {/* Tab bar */}
        <div className="flex overflow-x-auto border-b border-border scrollbar-hide">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-shrink-0 px-5 py-3.5 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-primary text-positive bg-primary/5"
                  : "border-transparent text-mutedText hover:text-neutralText hover:bg-bg/50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="p-5">
          {activeTab === "overview" && (
            <div className="space-y-5">
              {/* Relative Strength vs Nifty */}
              <RelativeStrengthCard
                ticker={company.ticker}
                price={fundamentals.current_price}
                dayChangePct={fundamentals.day_change_pct}
              />
              {/* Pros & Cons */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-bg border border-border rounded-lg p-4 space-y-2.5">
                  <div className="flex items-center gap-2 text-positive">
                    <CheckCircle2 className="w-4 h-4" />
                    <h3 className="font-heading font-bold text-sm text-neutralText">Strengths</h3>
                  </div>
                  {pros_cons.pros.length === 0 ? (
                    <p className="text-xs text-mutedText italic">No strengths computed — data may be incomplete.</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {pros_cons.pros.map((pro, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-xs text-neutralText">
                          <span className="w-1.5 h-1.5 rounded-full bg-positive mt-1.5 shrink-0" />
                          <span>{pro.text}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div className="bg-bg border border-border rounded-lg p-4 space-y-2.5">
                  <div className="flex items-center gap-2 text-negative">
                    <XCircle className="w-4 h-4" />
                    <h3 className="font-heading font-bold text-sm text-neutralText">Caution Flags</h3>
                  </div>
                  {pros_cons.cons.length === 0 ? (
                    <p className="text-xs text-mutedText italic">No caution flags triggered.</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {pros_cons.cons.map((con, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-xs text-neutralText">
                          <span className="w-1.5 h-1.5 rounded-full bg-negative mt-1.5 shrink-0" />
                          <span>{con.text}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              {/* Peer Comparison */}
              <div className="pt-2 border-t border-border">
                <PeerComparison currentTicker={company.ticker} />
              </div>
            </div>
          )}

          {activeTab === "growth" && <GrowthForecastChart ticker={company.ticker} />}

          {activeTab === "financials" && <FinancialStatements ticker={company.ticker} />}

          {activeTab === "quarterly" && <QuarterlyResults ticker={company.ticker} />}

          {activeTab === "ratios" && <RatioTrends ticker={company.ticker} />}

          {activeTab === "valuation" && (
            <div className="space-y-5">
              <DCFCalculator currentPrice={fundamentals.current_price} ticker={company.ticker} />
              <ValuationBandsChart ticker={company.ticker} />
              <ReverseDCFCard ticker={company.ticker} />
            </div>
          )}

          {activeTab === "supply-chain" && <SupplyChainGraph ticker={company.ticker} />}

          {activeTab === "forensic" && <ForensicRiskCard ticker={company.ticker} />}

          {activeTab === "shareholding" && <ShareholdingChart ticker={company.ticker} />}

          {activeTab === "research" && <ResearchDigestCard ticker={company.ticker} />}
        </div>
      </div>
    </div>
  );
}
