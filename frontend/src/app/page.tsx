"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Activity, TrendingUp, ShieldCheck, Brain, Sparkles } from "lucide-react";
import StockSearchInput from "@/components/StockSearchInput";
import SectorHeatmap from "@/components/SectorHeatmap";

const FEATURED_STOCKS = [
  { ticker: "RELIANCE.NS", name: "Reliance Industries", sector: "Energy & Oil" },
  { ticker: "TCS.NS", name: "Tata Consultancy Services", sector: "IT Services" },
  { ticker: "INFY.NS", name: "Infosys Ltd", sector: "IT Services" },
  { ticker: "HDFCBANK.NS", name: "HDFC Bank Ltd", sector: "Banking" },
  { ticker: "ICICIBANK.NS", name: "ICICI Bank Ltd", sector: "Banking" },
  { ticker: "TATAMOTORS.NS", name: "Tata Motors Ltd", sector: "Automobile" },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      {/* Hero Banner */}
      <div className="bg-surface border border-border rounded-card p-8 md:p-12 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl -z-0 pointer-events-none" />

        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 border border-primary/30 text-positive text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            ₹0-Budget Institutional-Grade NSE Intelligence
          </div>

          <h1 className="font-heading text-3xl md:text-5xl font-bold text-neutralText leading-tight">
            NSE Stock Research, NL Backtesting & Trading Psychology
          </h1>

          <p className="text-mutedText text-base md:text-lg leading-relaxed">
            Analyze Indian stocks with 5-axis Snowflake visual radar charts, backtest trading strategies in plain English, and diagnose your trading psychology habits — 100% deterministic, backed by code, not LLM hallucinations.
          </p>

          {/* Quick Search with Autocomplete Typeahead */}
          <div className="max-w-xl">
            <StockSearchInput
              placeholder="Search symbol or company (e.g. RELIANCE, TCS, INFY, BAJAJ-AUTO, WIPRO)..."
              buttonText="Analyze Stock"
            />
          </div>
        </div>
      </div>

      {/* Featured Stock Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-heading font-semibold text-xl text-neutralText">
            Quick Research — Blue-Chip NSE Stocks
          </h2>
          <span className="text-xs text-mutedText italic">Click any card for live analysis</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURED_STOCKS.map((stock) => (
            <Link
              key={stock.ticker}
              href={`/stock/${stock.ticker}`}
              className="bg-surface border border-border hover:border-primary/60 rounded-card p-5 transition-all group hover:-translate-y-0.5"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <h3 className="font-heading font-bold text-neutralText group-hover:text-primary transition-colors">
                    {stock.name}
                  </h3>
                  <span className="text-xs text-mutedText">{stock.ticker.replace(".NS","")} • {stock.sector}</span>
                </div>
                <span className="text-xs font-semibold text-primary/70 group-hover:text-primary transition-colors mt-0.5">
                  Analyze →
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Live Sector Heatmap */}
      <div className="space-y-3">
        <h2 className="font-heading font-semibold text-xl text-neutralText">NSE Sector Performance</h2>
        <SectorHeatmap />
      </div>

      {/* 4 Core Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-surface border border-border rounded-card p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center text-positive">
            <Activity className="w-5 h-5" />
          </div>
          <h3 className="font-heading font-bold text-neutralText text-lg">Snowflake Dashboard</h3>
          <p className="text-xs text-mutedText leading-relaxed">
            5-axis visual radar representation evaluating Value, Future, Past, Health, and Dividend.
          </p>
        </div>

        <div className="bg-surface border border-border rounded-card p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-secondary/20 border border-secondary/30 flex items-center justify-center text-secondary">
            <TrendingUp className="w-5 h-5" />
          </div>
          <h3 className="font-heading font-bold text-neutralText text-lg">NL Backtester</h3>
          <p className="text-xs text-mutedText leading-relaxed">
            Plain-English trading strategy engine mapping user text to a strict JSON schema and deterministic backtest.
          </p>
        </div>

        <div className="bg-surface border border-border rounded-card p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-positive/20 border border-positive/30 flex items-center justify-center text-positive">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h3 className="font-heading font-bold text-neutralText text-lg">Behavior Analyzer</h3>
          <p className="text-xs text-mutedText leading-relaxed">
            Upload trading CSV to diagnose habits: disposition effect, loss aversion, revenge trading, and position sizing.
          </p>
        </div>

        <div className="bg-surface border border-border rounded-card p-6 space-y-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Brain className="w-5 h-5" />
          </div>
          <h3 className="font-heading font-bold text-neutralText text-lg">Pseudo-Brain Digest</h3>
          <p className="text-xs text-mutedText leading-relaxed">
            Summarizes corporate filings, insider trades, and concalls with linked sources — numbers always come from code.
          </p>
        </div>
      </div>
    </div>
  );
}
