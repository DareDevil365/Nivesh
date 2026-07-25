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

  // Simplified DCF Fair Value Estimation
  const baseValue = currentPrice * 0.95;
  const estimatedFairValue = Math.round(
    baseValue * (1 + (revGrowth - 10) * 0.02) * (1 + (11 - discountRate) * 0.03) * (1 + (terminalGrowth - 3) * 0.02)
  );

  const discountPct = Math.round(((estimatedFairValue - currentPrice) / currentPrice) * 100);
  const isUndervalued = discountPct >= 0;

  return (
    <div className="bg-surface border border-border rounded-card p-6 space-y-6">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-secondary" />
          <h3 className="font-heading font-bold text-lg text-neutralText">
            Interactive DCF Valuation & Fair Value Model
          </h3>
        </div>
        <span className="text-xs text-mutedText">SimplyWall.st-style narrative calculator</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        {/* Sliders Control */}
        <div className="space-y-4 text-xs">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-mutedText font-semibold">5-Yr Projected Revenue Growth</span>
              <span className="font-bold text-positive">{revGrowth}%</span>
            </div>
            <input
              type="range"
              min="2"
              max="30"
              value={revGrowth}
              onChange={(e) => setRevGrowth(Number(e.target.value))}
              className="w-full accent-primary bg-bg"
            />
          </div>

          <div>
            <div className="flex justify-between mb-1">
              <span className="text-mutedText font-semibold">Discount Rate (WACC)</span>
              <span className="font-bold text-secondary">{discountRate}%</span>
            </div>
            <input
              type="range"
              min="8"
              max="16"
              value={discountRate}
              onChange={(e) => setDiscountRate(Number(e.target.value))}
              className="w-full accent-secondary bg-bg"
            />
          </div>

          <div>
            <div className="flex justify-between mb-1">
              <span className="text-mutedText font-semibold">Terminal Growth Rate</span>
              <span className="font-bold text-neutralText">{terminalGrowth}%</span>
            </div>
            <input
              type="range"
              min="2"
              max="6"
              value={terminalGrowth}
              onChange={(e) => setTerminalGrowth(Number(e.target.value))}
              className="w-full accent-primary bg-bg"
            />
          </div>
        </div>

        {/* Estimated Fair Value Display Box */}
        <div className="p-6 rounded-card bg-bg border border-border flex flex-col items-center justify-center text-center space-y-2">
          <div className="text-xs uppercase font-semibold text-mutedText">Estimated Fair Value</div>
          <div className="font-heading font-bold text-3xl text-neutralText">
            ₹{estimatedFairValue.toLocaleString("en-IN")}
          </div>

          <div
            className={`text-xs font-bold px-3 py-1 rounded-full border ${
              isUndervalued
                ? "bg-positive/20 text-positive border-positive/30"
                : "bg-negative/20 text-negative border-negative/30"
            }`}
          >
            {isUndervalued ? `Trading at ${discountPct}% Discount (Undervalued)` : `Trading at ${Math.abs(discountPct)}% Premium (Overvalued)`}
          </div>

          <p className="text-[11px] text-mutedText pt-2">
            Current Price: ₹{currentPrice.toLocaleString("en-IN")}
          </p>
        </div>
      </div>
    </div>
  );
}
