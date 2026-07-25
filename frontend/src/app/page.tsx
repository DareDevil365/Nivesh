"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, Activity, TrendingUp, ShieldCheck, Brain, ArrowRight, ShieldAlert, Sparkles } from "lucide-react";

const FEATURED_STOCKS = [
  { ticker: "RELIANCE.NS", name: "Reliance Industries", sector: "Energy & Oil", price: "₹2,980.50", change: "+1.25%" },
  { ticker: "TCS.NS", name: "Tata Consultancy Services", sector: "IT Services", price: "₹3,940.00", change: "+0.85%" },
  { ticker: "INFY.NS", name: "Infosys Ltd", sector: "IT Services", price: "₹1,620.40", change: "-0.40%" },
  { ticker: "HDFCBANK.NS", name: "HDFC Bank Ltd", sector: "Banking", price: "₹1,440.15", change: "+0.60%" },
  { ticker: "ICICIBANK.NS", name: "ICICI Bank Ltd", sector: "Banking", price: "₹1,090.00", change: "+1.10%" },
  { ticker: "TATAMOTORS.NS", name: "Tata Motors Ltd", sector: "Automobile", price: "₹965.80", change: "+2.30%" },
];

export default function HomePage() {
  const [tickerInput, setTickerInput] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!tickerInput.trim()) return;
    let ticker = tickerInput.trim().toUpperCase();
    if (!ticker.endsWith(".NS") && !ticker.endsWith(".BO")) {
      ticker = `${ticker}.NS`;
    }
    router.push(`/stock/${ticker}`);
  };

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

          {/* Quick Search */}
          <form onSubmit={handleSearch} className="flex gap-3 max-w-xl">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Enter stock symbol (e.g. RELIANCE, TCS, INFY)..."
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value)}
                className="w-full bg-bg border border-border rounded-lg pl-10 pr-4 py-3 text-sm text-neutralText placeholder:text-mutedText focus:outline-none focus:border-primary transition-colors"
              />
              <Search className="w-5 h-5 text-mutedText absolute left-3 top-3.5" />
            </div>
            <button
              type="submit"
              className="bg-primary hover:bg-primary/90 text-white font-medium px-6 py-3 rounded-lg text-sm transition-colors flex items-center gap-2"
            >
              Analyze <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>

      {/* Featured Stock Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-heading font-semibold text-xl text-neutralText">
            Popular NSE Stocks
          </h2>
          <span className="text-xs text-mutedText">Delayed ~15 min</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURED_STOCKS.map((stock) => (
            <Link
              key={stock.ticker}
              href={`/stock/${stock.ticker}`}
              className="bg-surface border border-border hover:border-primary/60 rounded-card p-5 transition-all group hover:-translate-y-0.5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-heading font-bold text-neutralText group-hover:text-primary transition-colors">
                    {stock.name}
                  </h3>
                  <span className="text-xs text-mutedText">{stock.ticker} • {stock.sector}</span>
                </div>
                <div className="text-right">
                  <div className="font-heading font-semibold text-neutralText">{stock.price}</div>
                  <span
                    className={`text-xs font-semibold ${
                      stock.change.startsWith("+") ? "text-positive" : "text-negative"
                    }`}
                  >
                    {stock.change}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* 4bundled Core Features Grid */}
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
