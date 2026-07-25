"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, Activity, Filter, Star, TrendingUp, ShieldCheck, Trophy } from "lucide-react";

export default function Header() {
  const [searchQuery, setSearchQuery] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    let ticker = searchQuery.trim().toUpperCase();
    if (!ticker.endsWith(".NS") && !ticker.endsWith(".BO")) {
      ticker = `${ticker}.NS`;
    }
    router.push(`/stock/${ticker}`);
  };

  return (
    <header className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center font-heading font-bold text-white text-lg shadow-sm">
            N
          </div>
          <span className="font-heading font-bold text-xl tracking-tight text-neutralText group-hover:text-primary transition-colors">
            NIVESH
          </span>
          <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded bg-primary/20 text-positive border border-primary/30">
            NSE
          </span>
        </Link>

        {/* Search Input */}
        <form onSubmit={handleSearch} className="flex-1 max-w-md relative">
          <input
            type="text"
            placeholder="Search ticker (e.g. RELIANCE, TCS, INFY, HDFCBANK)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-bg border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-neutralText placeholder:text-mutedText focus:outline-none focus:border-primary transition-colors"
          />
          <Search className="w-4 h-4 text-mutedText absolute left-3 top-2.5" />
        </form>

        {/* Nav Links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-mutedText">
          <Link
            href="/stock/RELIANCE.NS"
            className="flex items-center gap-1.5 hover:text-neutralText transition-colors"
          >
            <Activity className="w-4 h-4 text-primary" />
            Dashboard
          </Link>

          <Link
            href="/screener"
            className="flex items-center gap-1.5 hover:text-neutralText transition-colors"
          >
            <Filter className="w-4 h-4 text-positive" />
            Screener
          </Link>

          <Link
            href="/watchlist"
            className="flex items-center gap-1.5 hover:text-neutralText transition-colors"
          >
            <Star className="w-4 h-4 text-secondary" />
            Watchlist
          </Link>

          <Link
            href="/backtester"
            className="flex items-center gap-1.5 hover:text-neutralText transition-colors"
          >
            <TrendingUp className="w-4 h-4 text-secondary" />
            Backtester
          </Link>

          <Link
            href="/behavior"
            className="flex items-center gap-1.5 hover:text-neutralText transition-colors"
          >
            <ShieldCheck className="w-4 h-4 text-positive" />
            Behavior
          </Link>

          <Link
            href="/leaderboard"
            className="flex items-center gap-1.5 hover:text-neutralText transition-colors"
          >
            <Trophy className="w-4 h-4 text-amber-400" />
            Leaderboard
          </Link>
        </nav>

        {/* Data Honesty Badge */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-xs text-mutedText bg-bg px-2.5 py-1 rounded-full border border-border">
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
            Delayed ~15 min
          </span>
        </div>
      </div>
    </header>
  );
}
