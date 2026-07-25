"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Grid, TrendingUp, TrendingDown } from "lucide-react";

interface SectorData {
  sector: string;
  total_market_cap: number;
  avg_change_pct: number;
  stock_count: number;
  top_stocks: Array<{ ticker: string; name: string; change_pct: number }>;
}

export default function SectorHeatmap() {
  const [heatmap, setHeatmap] = useState<SectorData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHeatmap() {
      try {
        const res = await fetch("http://localhost:8000/api/screener/sector-heatmap");
        if (res.ok) {
          const data = await res.json();
          setHeatmap(data.heatmap || []);
        }
      } catch (err) {
        // Fallback sample sector heatmap if local backend starting
        setHeatmap([
          { sector: "Information Technology", total_market_cap: 3500000000000, avg_change_pct: 1.15, stock_count: 2, top_stocks: [{ ticker: "TCS.NS", name: "TCS", change_pct: 0.85 }, { ticker: "INFY.NS", name: "Infosys", change_pct: 1.45 }] },
          { sector: "Financial Services", total_market_cap: 4200000000000, avg_change_pct: 0.85, stock_count: 3, top_stocks: [{ ticker: "HDFCBANK.NS", name: "HDFC Bank", change_pct: 0.60 }, { ticker: "ICICIBANK.NS", name: "ICICI Bank", change_pct: 1.10 }] },
          { sector: "Energy & Oil", total_market_cap: 2900000000000, avg_change_pct: -0.45, stock_count: 1, top_stocks: [{ ticker: "RELIANCE.NS", name: "Reliance", change_pct: -0.45 }] },
          { sector: "Automobile", total_market_cap: 1800000000000, avg_change_pct: 2.30, stock_count: 1, top_stocks: [{ ticker: "TATAMOTORS.NS", name: "Tata Motors", change_pct: 2.30 }] },
        ]);
      } finally {
        setLoading(false);
      }
    }
    fetchHeatmap();
  }, []);

  if (loading) {
    return <div className="h-32 bg-surface animate-pulse rounded-card" />;
  }

  return (
    <div className="bg-surface border border-border rounded-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Grid className="w-5 h-5 text-secondary" />
          <h2 className="font-heading font-bold text-lg text-neutralText">
            NSE Sector Performance Heatmap
          </h2>
        </div>
        <span className="text-xs text-mutedText">Tijori-style sector framing</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {heatmap.map((sec) => {
          const isUp = sec.avg_change_pct >= 0;
          return (
            <div
              key={sec.sector}
              className={`p-4 rounded-lg border transition-all ${
                isUp
                  ? "bg-positive/5 border-positive/20 hover:border-positive/40"
                  : "bg-negative/5 border-negative/20 hover:border-negative/40"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-heading font-bold text-sm text-neutralText">
                  {sec.sector}
                </span>
                <span
                  className={`text-xs font-bold px-2 py-0.5 rounded flex items-center gap-1 ${
                    isUp ? "bg-positive/20 text-positive" : "bg-negative/20 text-negative"
                  }`}
                >
                  {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  {isUp ? "+" : ""}{sec.avg_change_pct}%
                </span>
              </div>

              <div className="text-[11px] text-mutedText mb-3">
                Market Cap: ₹{(sec.total_market_cap / 100000000000).toFixed(1)} Lakh Cr
              </div>

              <div className="space-y-1 pt-2 border-t border-border/50">
                {sec.top_stocks.map((stk) => (
                  <Link
                    key={stk.ticker}
                    href={`/stock/${stk.ticker}`}
                    className="flex items-center justify-between text-xs hover:text-primary transition-colors"
                  >
                    <span className="text-mutedText">{stk.name}</span>
                    <span className={stk.change_pct >= 0 ? "text-positive font-semibold" : "text-negative font-semibold"}>
                      {stk.change_pct >= 0 ? "+" : ""}{stk.change_pct}%
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
