"use client";

import React, { useState } from "react";

const GLOSSARY_TERMS: Record<string, string> = {
  "P/E Ratio": "Price-to-Earnings ratio measures stock price relative to trailing 12-month earnings per share. Lower multiples may signal relative value.",
  "P/B Ratio": "Price-to-Book ratio compares market price to net asset value per share.",
  "ROE": "Return on Equity measures profitability relative to shareholder capital. Higher than 15% indicates strong capital efficiency.",
  "ROCE": "Return on Capital Employed measures returns generated from both equity and debt capital.",
  "Debt / Equity": "Debt-to-Equity ratio measures financial leverage. Ratios under 0.5 indicate a conservative, healthy balance sheet.",
  "Dividend Yield": "Annual dividend payment divided by current share price, expressed as a percentage.",
  "RSI": "Relative Strength Index (14) momentum oscillator ranging 0-100. Below 30 suggests oversold conditions, above 70 suggests overbought.",
  "MACD": "Moving Average Convergence Divergence tracks trend strength and direction by measuring differences between moving averages.",
  "Snowflake": "Simplywall.st-style 5-pillar visual analysis evaluating Value, Future, Past, Health, and Dividend strength.",
  "Promoter Holding": "Percentage of share capital owned by founding promoters. High holding (>50%) reflects strong insider confidence."
};

interface GlossaryTooltipProps {
  term: string;
  children?: React.ReactNode;
}

export default function GlossaryTooltip({ term, children }: GlossaryTooltipProps) {
  const [show, setShow] = useState(false);
  const definition = GLOSSARY_TERMS[term] || `${term}: Key financial performance metric.`;

  return (
    <span
      className="relative inline-block cursor-help border-b border-dotted border-mutedText hover:border-positive transition-colors"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children || term}
      {show && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-surface border border-border rounded-lg shadow-xl text-xs text-neutralText z-50 pointer-events-none animate-in fade-in">
          <div className="font-heading font-bold text-positive mb-1">{term}</div>
          <p className="text-[11px] text-mutedText leading-snug">{definition}</p>
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-surface" />
        </div>
      )}
    </span>
  );
}
