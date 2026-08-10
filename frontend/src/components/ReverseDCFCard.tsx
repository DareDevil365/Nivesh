"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Calculator, Sparkles, Loader2, Info } from "lucide-react";

interface ReverseDCFData {
  ticker: string;
  current_price: number;
  reverse_dcf: {
    implied_growth_pct: number;
    discount_rate_wacc_pct: number;
    terminal_growth_pct: number;
    explanation: string;
    matrix: {
      bear_target: number;
      base_target: number;
      bull_target: number;
    };
  };
}

export default function ReverseDCFCard({ ticker }: { ticker: string }) {
  const [data, setData] = useState<ReverseDCFData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchReverseDCF() {
      setLoading(true);
      try {
        const res = await api.get<ReverseDCFData>(`/api/companies/${ticker}/valuation-bands`);
        setData(res);
      } catch (err) {
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchReverseDCF();
  }, [ticker]);

  if (loading) {
    return (
      <div className="h-44 border border-border bg-surface rounded-card flex items-center justify-center gap-2 text-mutedText text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Solving Reverse DCF Market Implied Growth…
      </div>
    );
  }

  if (!data) return null;

  const { reverse_dcf, current_price } = data;
  const { matrix } = reverse_dcf;

  return (
    <div className="border border-border bg-surface rounded-card p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-secondary" />
          <h3 className="font-heading font-bold text-lg text-neutralText">
            Reverse DCF — Market Implied Growth & Scenario Matrix
          </h3>
        </div>
        <span className="text-xs text-mutedText">Market Expectation Solver</span>
      </div>

      {/* Implied Growth Banner */}
      <div className="p-4 rounded-card bg-bg border border-border flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="space-y-1 text-center md:text-left">
          <div className="text-xs font-semibold text-mutedText uppercase">Market Implied 5-Yr FCF Growth Rate</div>
          <div className="font-heading font-bold text-3xl text-positive">
            {reverse_dcf.implied_growth_pct}% / Year
          </div>
          <p className="text-xs text-mutedText">{reverse_dcf.explanation}</p>
        </div>

        <div className="px-4 py-2 rounded-lg bg-surface border border-border text-center flex-shrink-0">
          <span className="text-[10px] uppercase font-semibold text-mutedText">WACC Discount Rate</span>
          <div className="font-heading font-bold text-base text-neutralText">{reverse_dcf.discount_rate_wacc_pct}%</div>
        </div>
      </div>

      {/* Bear / Base / Bull Target Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-negative/5 border border-negative/20 text-center space-y-1">
          <span className="text-xs font-bold text-negative">Bear Case Target</span>
          <div className="font-heading font-bold text-2xl text-neutralText">₹{matrix.bear_target.toLocaleString("en-IN")}</div>
          <div className="text-[11px] text-mutedText">8% FCF Growth · 12% WACC</div>
        </div>

        <div className="p-4 rounded-lg bg-primary/10 border border-primary/30 text-center space-y-1 ring-1 ring-primary/30">
          <span className="text-xs font-bold text-positive">Base Case Target</span>
          <div className="font-heading font-bold text-2xl text-neutralText">₹{matrix.base_target.toLocaleString("en-IN")}</div>
          <div className="text-[11px] text-mutedText">12% FCF Growth · 11% WACC</div>
        </div>

        <div className="p-4 rounded-lg bg-positive/5 border border-positive/20 text-center space-y-1">
          <span className="text-xs font-bold text-positive">Bull Case Target</span>
          <div className="font-heading font-bold text-2xl text-neutralText">₹{matrix.bull_target.toLocaleString("en-IN")}</div>
          <div className="text-[11px] text-mutedText">18% FCF Growth · 10% WACC</div>
        </div>
      </div>
    </div>
  );
}
