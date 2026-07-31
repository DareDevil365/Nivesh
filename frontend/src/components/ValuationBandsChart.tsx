"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TrendingUp, Loader2, Info } from "lucide-react";

interface BandsData {
  ticker: string;
  current_price: number;
  pe_bands: {
    median: number;
    plus_1sd: number;
    minus_1sd: number;
    plus_2sd: number;
    minus_2sd: number;
    current: number;
  };
  pb_bands: {
    median: number;
    plus_1sd: number;
    minus_1sd: number;
    plus_2sd: number;
    minus_2sd: number;
    current: number;
  };
  valuation_zone: string;
  valuation_status: string;
  valuation_comment: string;
}

export default function ValuationBandsChart({ ticker }: { ticker: string }) {
  const [data, setData] = useState<BandsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<"pe" | "pb">("pe");

  useEffect(() => {
    async function fetchBands() {
      setLoading(true);
      try {
        const res = await api.get<BandsData>(`/api/companies/${ticker}/valuation-bands`);
        setData(res);
      } catch (err) {
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchBands();
  }, [ticker]);

  if (loading) {
    return (
      <div className="h-44 border border-border bg-surface rounded-card flex items-center justify-center gap-2 text-mutedText text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Calculating Historical Valuation Bands…
      </div>
    );
  }

  if (!data) return null;

  const bands = mode === "pe" ? data.pe_bands : data.pb_bands;
  const unit = mode === "pe" ? "P/E Ratio" : "P/B Ratio";

  return (
    <div className="border border-border bg-surface rounded-card p-6 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-primary" />
            5-Year Historical Valuation Band Matrix
          </h3>
          <p className="text-xs text-mutedText mt-0.5">
            {data.valuation_comment}
          </p>
        </div>

        <div className="flex items-center gap-1 bg-bg p-1 rounded-lg border border-border">
          <button
            onClick={() => setMode("pe")}
            className={`px-3 py-1 text-xs font-semibold rounded transition-colors ${
              mode === "pe" ? "bg-primary text-white" : "text-mutedText hover:text-neutralText"
            }`}
          >
            P/E Bands
          </button>
          <button
            onClick={() => setMode("pb")}
            className={`px-3 py-1 text-xs font-semibold rounded transition-colors ${
              mode === "pb" ? "bg-primary text-white" : "text-mutedText hover:text-neutralText"
            }`}
          >
            P/B Bands
          </button>
        </div>
      </div>

      {/* Visual Band Distribution Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3 rounded-lg border border-negative/30 bg-negative/5 text-center">
          <div className="text-[10px] text-mutedText uppercase font-semibold">+2SD (Overvalued)</div>
          <div className="font-heading font-bold text-lg text-negative">{bands.plus_2sd}x</div>
        </div>

        <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/5 text-center">
          <div className="text-[10px] text-mutedText uppercase font-semibold">+1SD (Upper Band)</div>
          <div className="font-heading font-bold text-lg text-amber-400">{bands.plus_1sd}x</div>
        </div>

        <div className="p-3 rounded-lg border border-primary/40 bg-primary/10 text-center ring-2 ring-primary/40">
          <div className="text-[10px] text-primary uppercase font-bold">5-Yr Median</div>
          <div className="font-heading font-bold text-xl text-positive">{bands.median}x</div>
          <div className="text-[9px] text-mutedText">Current: {bands.current}x</div>
        </div>

        <div className="p-3 rounded-lg border border-secondary/30 bg-secondary/5 text-center">
          <div className="text-[10px] text-mutedText uppercase font-semibold">-1SD (Value Zone)</div>
          <div className="font-heading font-bold text-lg text-secondary">{bands.minus_1sd}x</div>
        </div>

        <div className="p-3 rounded-lg border border-positive/30 bg-positive/5 text-center col-span-2 sm:col-span-1">
          <div className="text-[10px] text-mutedText uppercase font-semibold">-2SD (Bargain Trough)</div>
          <div className="font-heading font-bold text-lg text-positive">{bands.minus_2sd}x</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs p-3 rounded bg-bg border border-border">
        <span className="text-mutedText">Valuation Status:</span>
        <span
          className={`font-bold px-2.5 py-0.5 rounded text-xs ${
            data.valuation_status === "positive"
              ? "bg-positive/20 text-positive"
              : data.valuation_status === "negative"
              ? "bg-negative/20 text-negative"
              : "bg-amber-500/20 text-amber-400"
          }`}
        >
          {data.valuation_zone}
        </span>
      </div>
    </div>
  );
}
