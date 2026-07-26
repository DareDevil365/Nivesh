"use client";

import React from "react";
import Link from "next/link";
import { TrendingUp, ShieldAlert, Heart, Github } from "lucide-react";

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-surface border-t border-border mt-16 py-8 text-xs text-mutedText">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Brand & Tagline */}
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-primary/20 border border-primary/30 flex items-center justify-center text-primary">
              <TrendingUp className="w-4 h-4" />
            </div>
            <span className="font-heading font-bold text-sm text-neutralText tracking-tight">
              NIVESH <span className="text-[10px] font-normal text-primary">NSE</span>
            </span>
            <span className="text-mutedText/60">|</span>
            <span>Indian Equity Research & Backtesting Sandbox</span>
          </div>

          {/* Quick Nav Links */}
          <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-neutralText/80">
            <Link href="/stock/RELIANCE.NS" className="hover:text-primary transition-colors">
              Research
            </Link>
            <Link href="/screener" className="hover:text-primary transition-colors">
              Screener
            </Link>
            <Link href="/backtester" className="hover:text-primary transition-colors">
              Backtester
            </Link>
            <Link href="/behavior" className="hover:text-primary transition-colors">
              Behavior Analyzer
            </Link>
            <Link href="/leaderboard" className="hover:text-primary transition-colors">
              Leaderboard
            </Link>
          </div>
        </div>

        {/* Disclaimer & Data Honesty Notice */}
        <div className="p-3 rounded-lg bg-bg/50 border border-border/50 text-[11px] leading-relaxed text-mutedText flex items-start gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-neutralText">Financial Disclosure & Data Note:</span> Intraday NSE quotes are polled with a 60s Redis TTL and marked with a delayed badge (~15 min). Backtest results and behavioral metrics are for educational research purposes only and do not constitute financial advice. Always verify filings with official exchange disclosures.
          </div>
        </div>

        {/* Footer Bottom Line */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 pt-2 border-t border-border/40 text-[11px]">
          <p>© 2026 Nivesh. ₹0-budget Institutional-Grade Analytics Platform.</p>
          <div className="flex items-center gap-1 text-mutedText">
            <span>Built with</span>
            <Heart className="w-3 h-3 text-red-500 fill-red-500" />
            <span>for Indian Retail Investors</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
