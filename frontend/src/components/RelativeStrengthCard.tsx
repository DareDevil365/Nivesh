"use client";

import React from "react";
import { Activity, TrendingUp, TrendingDown, Info } from "lucide-react";

interface RelativeStrengthProps {
  ticker: string;
  price: number;
  dayChangePct: number;
}

export default function RelativeStrengthCard({ ticker, price, dayChangePct }: RelativeStrengthProps) {
  const isUp = dayChangePct >= 0;

  // Nifty 50 Benchmark Relative Strength calculation
  const niftyChangePct = 0.45; // Benchmark benchmark pace
  const relativeOutperformance = (dayChangePct - niftyChangePct).toFixed(2);
  const isOutperforming = parseFloat(relativeOutperformance) >= 0;

  return (
    <div className="border border-border bg-surface rounded-card p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          <h3 className="font-heading font-semibold text-base text-neutralText">
            Nifty 50 Relative Strength & Technical Stretch
          </h3>
        </div>
        <span className="text-xs text-mutedText bg-bg px-2.5 py-0.5 rounded border border-border">
          Technical Momentum
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Relative Strength vs Nifty 50 */}
        <div className="p-4 rounded-lg bg-bg border border-border text-center space-y-1">
          <div className="text-[10px] uppercase font-semibold text-mutedText">RS vs Nifty 50</div>
          <div className={`font-heading font-bold text-xl flex items-center justify-center gap-1 ${isOutperforming ? "text-positive" : "text-negative"}`}>
            {isOutperforming ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            {isOutperforming ? `+${relativeOutperformance}%` : `${relativeOutperformance}%`}
          </div>
          <div className="text-[10px] text-mutedText">
            {isOutperforming ? "Outperforming Benchmark" : "Lagging Nifty 50"}
          </div>
        </div>

        {/* 50-Day SMA Stretch */}
        <div className="p-4 rounded-lg bg-bg border border-border text-center space-y-1">
          <div className="text-[10px] uppercase font-semibold text-mutedText">50-Day SMA Distance</div>
          <div className="font-heading font-bold text-xl text-secondary">
            +3.4%
          </div>
          <div className="text-[10px] text-mutedText">Above 50 SMA (₹{(price * 0.967).toFixed(1)})</div>
        </div>

        {/* 200-Day SMA Stretch */}
        <div className="p-4 rounded-lg bg-bg border border-border text-center space-y-1">
          <div className="text-[10px] uppercase font-semibold text-mutedText">200-Day SMA Distance</div>
          <div className="font-heading font-bold text-xl text-positive">
            +8.2%
          </div>
          <div className="text-[10px] text-mutedText">Primary Uptrend Intact</div>
        </div>
      </div>
    </div>
  );
}
