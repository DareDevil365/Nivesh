"use client";

import React, { useState } from "react";
import { Calculator, Sparkles, HelpCircle } from "lucide-react";
import GlossaryTooltip from "./GlossaryTooltip";

interface DCFCalculatorProps {
  currentPrice: number;
  ticker: string;
}

export default function DCFCalculator({ currentPrice, ticker }: DCFCalculatorProps) {
  const [revGrowth, setRevGrowth] = useState<number>(12.0);
  const [discountRate, setDiscountRate] = useState<number>(11.0);
  const [terminalGrowth, setTerminalGrowth] = useState<number>(4.0);

  // Realistic 2-stage DCF calculation
  // Stage 1: 5-year cash flow projection
  let pvCashFlows = 0;
  let currentFCF = Math.max(1, currentPrice * 0.045); // Baseline Free Cash Flow yield per share (~4.5%)
  const r = Math.max(0.05, discountRate / 100.0);
  const g = revGrowth / 100.0;
  const t_g = Math.min(r - 0.01, terminalGrowth / 100.0); // Ensure discount rate > terminal growth

  const projectedFCFs: { year: number; fcf: number; pv: number }[] = [];
  for (let yr = 1; yr <= 5; yr++) {
    currentFCF = currentFCF * (1 + g);
    const pv = currentFCF / Math.pow(1 + r, yr);
    pvCashFlows += pv;
    projectedFCFs.push({ year: yr, fcf: Math.round(currentFCF * 100) / 100, pv: Math.round(pv * 100) / 100 });
  }

  // Stage 2: Terminal Value (Gordon Growth Model)
  const terminalVal = (currentFCF * (1 + t_g)) / Math.max(0.01, r - t_g);
  const pvTerminalVal = terminalVal / Math.pow(1 + r, 5);
  const fairValuePerShare = pvCashFlows + pvTerminalVal;

  const estimatedFairValue = Math.max(1, Math.round(fairValuePerShare));
  const discountPct = currentPrice > 0 ? Math.round(((estimatedFairValue - currentPrice) / currentPrice) * 100) : 0;
  const isUndervalued = discountPct >= 0;

  return (
    <div className="bg-surface border border-border rounded-card p-6 space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-secondary" />
          <h3 className="font-heading font-bold text-lg text-neutralText">
            Interactive 2-Stage DCF Valuation Model ({ticker})
          </h3>
        </div>
        <span className="text-xs text-mutedText font-semibold">Institutional Discounted Cash Flow</span>
      </div>

      {/* FCF Assumption Disclaimer */}
      <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/8 border border-amber-500/20 text-xs text-amber-300">
        <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
        <span>
          <strong>Illustration model:</strong> FCF baseline assumed at ~4.5% yield of current price.
          For precision, cross-check against actual Free Cash Flow per share from the Financials tab.
          Adjust growth and discount sliders to model your own assumptions.
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Sliders Control */}
        <div className="space-y-5 text-xs">
          <div>
            <div className="flex justify-between mb-1.5">
              <span className="text-mutedText font-semibold">5-Yr Projected Growth Rate</span>
              <span className="font-bold text-positive">{revGrowth}%</span>
            </div>
            <input
              type="range"
              min="2"
              max="30"
              value={revGrowth}
              onChange={(e) => setRevGrowth(Number(e.target.value))}
              className="w-full accent-primary bg-bg cursor-pointer"
            />
            <p className="text-[10px] text-mutedText mt-1">Expected annual Free Cash Flow growth over next 5 years.</p>
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <span className="text-mutedText font-semibold">Discount Rate (WACC)</span>
              <span className="font-bold text-secondary">{discountRate}%</span>
            </div>
            <input
              type="range"
              min="8"
              max="16"
              value={discountRate}
              onChange={(e) => setDiscountRate(Number(e.target.value))}
              className="w-full accent-secondary bg-bg cursor-pointer"
            />
            <p className="text-[10px] text-mutedText mt-1">Required rate of return based on cost of equity and debt risk.</p>
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <span className="text-mutedText font-semibold">Terminal Growth Rate</span>
              <span className="font-bold text-neutralText">{terminalGrowth}%</span>
            </div>
            <input
              type="range"
              min="2"
              max="6"
              value={terminalGrowth}
              onChange={(e) => setTerminalGrowth(Number(e.target.value))}
              className="w-full accent-primary bg-bg cursor-pointer"
            />
            <p className="text-[10px] text-mutedText mt-1">Long-term GDP growth cap rate after Year 5.</p>
          </div>
        </div>

        {/* Estimated Fair Value Display Box */}
        <div className="p-6 rounded-card bg-bg border border-border flex flex-col items-center justify-center text-center space-y-3">
          <div className="text-xs uppercase font-semibold text-mutedText tracking-wider">Intrinsic Fair Value / Share</div>
          <div className="font-heading font-bold text-3xl text-neutralText">
            ₹{estimatedFairValue.toLocaleString("en-IN")}
          </div>

          <div
            className={`text-xs font-bold px-3.5 py-1.5 rounded-full border ${
              isUndervalued
                ? "bg-positive/20 text-positive border-positive/30"
                : "bg-negative/20 text-negative border-negative/30"
            }`}
          >
            {isUndervalued ? `Trading at ${discountPct}% Discount (Undervalued)` : `Trading at ${Math.abs(discountPct)}% Premium (Overvalued)`}
          </div>

          <div className="w-full grid grid-cols-2 gap-2 text-[11px] pt-2 border-t border-border/50 text-left">
            <div>
              <span className="text-mutedText block">Current Price:</span>
              <span className="font-semibold text-neutralText">₹{currentPrice.toLocaleString("en-IN")}</span>
            </div>
            <div>
              <span className="text-mutedText block">PV 5-Yr FCF:</span>
              <span className="font-semibold text-neutralText">₹{Math.round(pvCashFlows).toLocaleString("en-IN")}</span>
            </div>
            <div>
              <span className="text-mutedText block">PV Terminal Value:</span>
              <span className="font-semibold text-neutralText">₹{Math.round(pvTerminalVal).toLocaleString("en-IN")}</span>
            </div>
            <div>
              <span className="text-mutedText block">Terminal Value %:</span>
              <span className="font-semibold text-neutralText">{Math.round((pvTerminalVal / (pvCashFlows + pvTerminalVal)) * 100)}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
