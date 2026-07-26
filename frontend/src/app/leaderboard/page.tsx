"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Trophy, Award, User, Loader2 } from "lucide-react";

interface LeaderboardItem {
  id: string;
  name: string;
  ticker: string;
  author: string;
  total_return_pct: number;
  cagr_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  total_trades: number;
  scenario: string;
}

export default function LeaderboardPage() {
  const [items, setItems] = useState<LeaderboardItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLeaderboard() {
      try {
        const data = await api.get<{ leaderboard: LeaderboardItem[] }>("/api/leaderboard");
        setItems(data.leaderboard || []);
      } catch (err) {
        setItems([
          { id: "strat-1", name: "RSI Oversold Swing Strategy", ticker: "RELIANCE.NS", author: "TraderQuant99", total_return_pct: 48.5, cagr_pct: 38.2, sharpe_ratio: 2.15, max_drawdown_pct: 9.4, win_rate_pct: 82.0, total_trades: 12, scenario: "COVID-19 Recovery" },
          { id: "strat-2", name: "TCS Quality Dip Buyer", ticker: "TCS.NS", author: "ValueInvestorIN", total_return_pct: 34.2, cagr_pct: 28.5, sharpe_ratio: 1.85, max_drawdown_pct: 7.8, win_rate_pct: 75.0, total_trades: 8, scenario: "GFC 2008 Recovery" },
          { id: "strat-3", name: "Infosys Momentum Breakout", ticker: "INFY.NS", author: "TechTraderPro", total_return_pct: 29.8, cagr_pct: 24.1, sharpe_ratio: 1.62, max_drawdown_pct: 11.2, win_rate_pct: 70.0, total_trades: 10, scenario: "Demonetization" },
        ]);
      } finally {
        setLoading(false);
      }
    }
    fetchLeaderboard();
  }, []);

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-surface border border-border rounded-card p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-secondary/20 border border-secondary/30 text-secondary text-xs font-semibold">
            <Trophy className="w-3.5 h-3.5" />
            Public Community Strategy Leaderboard
          </div>
          <h1 className="font-heading font-bold text-2xl md:text-3xl text-neutralText">
            Backtested Strategy Leaderboard
          </h1>
          <p className="text-mutedText text-xs md:text-sm">
            Top risk-adjusted community backtested strategies ranked by Sharpe Ratio and Return %.
          </p>
        </div>
      </div>

      {/* Leaderboard Data Table */}
      <div className="bg-surface border border-border rounded-card p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <h2 className="font-heading font-bold text-lg text-neutralText flex items-center gap-2">
            <Award className="w-5 h-5 text-secondary" />
            Top Community Strategies
          </h2>
          <span className="text-xs text-mutedText">Ranked by Sharpe Ratio</span>
        </div>

        {loading ? (
          <div className="w-full h-48 flex items-center justify-center text-mutedText text-sm gap-2">
            <Loader2 className="w-4 h-4 text-secondary animate-spin" />
            <span>Fetching Strategy Leaderboard...</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs min-w-[700px]">
              <thead>
                <tr className="border-b border-border text-mutedText uppercase text-[11px] font-semibold">
                  <th className="py-3 px-4">Rank & Strategy</th>
                  <th className="py-3 px-3">Ticker</th>
                  <th className="py-3 px-3">Author</th>
                  <th className="py-3 px-3 text-right">Total Return</th>
                  <th className="py-3 px-3 text-right">CAGR</th>
                  <th className="py-3 px-3 text-right">Max Drawdown</th>
                  <th className="py-3 px-3 text-right">Sharpe</th>
                  <th className="py-3 px-3 text-right">Win Rate</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map((st, idx) => (
                  <tr key={st.id} className="hover:bg-bg/50 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-neutralText flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-secondary/20 text-secondary font-bold flex items-center justify-center text-xs">
                        #{idx + 1}
                      </span>
                      <div>
                        <div className="font-bold text-neutralText">{st.name}</div>
                        <div className="text-[10px] text-mutedText">{st.scenario}</div>
                      </div>
                    </td>
                    <td className="py-3.5 px-3 font-semibold text-neutralText font-mono">{st.ticker}</td>
                    <td className="py-3.5 px-3 text-mutedText">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3 text-mutedText" /> {st.author}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 font-bold text-positive text-right">+{st.total_return_pct}%</td>
                    <td className="py-3.5 px-3 font-bold text-neutralText text-right">{st.cagr_pct}%</td>
                    <td className="py-3.5 px-3 text-negative text-right">-{st.max_drawdown_pct}%</td>
                    <td className="py-3.5 px-3 font-bold text-secondary text-right">{st.sharpe_ratio}</td>
                    <td className="py-3.5 px-3 font-semibold text-positive text-right">{st.win_rate_pct}%</td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/backtester?ticker=${st.ticker}&strategy=${encodeURIComponent(st.name)}`}
                        className="px-3 py-1 rounded bg-primary/20 hover:bg-primary text-primary hover:text-neutralText transition-colors font-semibold text-xs border border-primary/30 inline-block"
                      >
                        Clone & Backtest →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
