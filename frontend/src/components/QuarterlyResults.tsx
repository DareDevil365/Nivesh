"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BarChart3, Loader2, TrendingUp, TrendingDown, AlertCircle } from "lucide-react";

interface QuarterlyRow {
  metric: string;
  values: (number | null)[];
  unit: string;
  highlight: boolean;
}

interface QuarterlyData {
  ticker: string;
  quarters: string[];
  rows: QuarterlyRow[];
  data_source: string;
  message?: string;
}

interface QuarterlyResultsProps {
  ticker: string;
}

function fmt(val: number | null, unit: string): string {
  if (val === null || val === undefined) return "—";
  if (unit === "%") return `${val.toFixed(1)}%`;
  if (unit === "₹ Cr") {
    if (Math.abs(val) >= 100000) return `₹${(val / 100000).toFixed(1)}L Cr`;
    if (Math.abs(val) >= 1000) return `₹${(val / 1000).toFixed(1)}K Cr`;
    return `₹${val.toLocaleString("en-IN")} Cr`;
  }
  return String(val);
}

function growthColor(curr: number | null, prev: number | null): string {
  if (curr === null || prev === null || prev === 0) return "text-mutedText";
  const g = ((curr - prev) / Math.abs(prev)) * 100;
  if (g > 0) return "text-positive";
  if (g < 0) return "text-negative";
  return "text-mutedText";
}

function growthPct(curr: number | null, prev: number | null): string {
  if (curr === null || prev === null || prev === 0) return "";
  const g = ((curr - prev) / Math.abs(prev)) * 100;
  return `${g >= 0 ? "+" : ""}${g.toFixed(1)}%`;
}

export default function QuarterlyResults({ ticker }: QuarterlyResultsProps) {
  const [data, setData] = useState<QuarterlyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get<QuarterlyData>(`/api/companies/${ticker}/quarterly-results`);
        setData(res);
      } catch (e: any) {
        setError(e.message || "Failed to load quarterly results");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker]);

  if (loading) {
    return (
      <div className="border border-border bg-surface rounded-card p-6 flex items-center justify-center gap-2 h-48 text-mutedText text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Loading Quarterly Results…
      </div>
    );
  }

  if (!data || data.data_source === "unavailable" || !data.rows.length) {
    return (
      <div className="border border-border bg-surface rounded-card p-6 space-y-3">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          Quarterly Results
        </h3>
        <div className="flex items-start gap-2 p-4 bg-bg rounded-lg border border-border/60 text-xs text-mutedText">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            {data?.message || "Quarterly financial data is not available for this stock from the current data source."}
          </span>
        </div>
      </div>
    );
  }

  const quarters = data.quarters;
  // Show last 8 quarters max
  const displayCols = Math.min(quarters.length, 8);
  const qSlice = quarters.slice(-displayCols);

  // Key rows that should be highlighted (section headers)
  const HIGHLIGHT_ROWS = new Set(["Operating Profit", "Net Profit", "EBITDA", "Profit Before Tax"]);
  const PCT_ROWS = new Set(["OPM %", "Tax %", "NPM %"]);

  return (
    <div className="border border-border bg-surface rounded-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          Quarterly Results
          <span className="text-xs text-mutedText font-normal ml-1">(₹ Crores)</span>
        </h3>
        <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-semibold">
          Last {displayCols} Quarters
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs min-w-[700px]">
          <thead>
            <tr className="bg-bg border-b border-border">
              <th className="p-3 text-left font-semibold text-mutedText w-40 sticky left-0 bg-bg z-10">
                Metric
              </th>
              {qSlice.map((q, i) => (
                <th key={i} className="p-3 text-right font-semibold text-mutedText whitespace-nowrap">
                  {q}
                </th>
              ))}
              <th className="p-3 text-right font-semibold text-mutedText whitespace-nowrap">
                YoY Chg
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {data.rows.map((row, idx) => {
              const isHighlight = HIGHLIGHT_ROWS.has(row.metric) || row.highlight;
              const isPct = PCT_ROWS.has(row.metric) || row.unit === "%";
              const vals = row.values.slice(-displayCols);

              // YoY change: compare last value vs same-quarter last year (4 quarters back)
              const lastVal = vals[vals.length - 1];
              const yoyVal = vals.length >= 5 ? vals[vals.length - 5] : null;

              return (
                <tr
                  key={idx}
                  className={`transition-colors hover:bg-bg/40 ${
                    isHighlight ? "font-semibold bg-bg/20" : ""
                  }`}
                >
                  <td
                    className={`p-3 text-left sticky left-0 z-10 ${
                      isHighlight ? "bg-surface text-neutralText font-semibold border-r border-border/40" : "bg-surface text-mutedText border-r border-border/40"
                    }`}
                  >
                    {row.metric}
                  </td>

                  {vals.map((v, i) => {
                    const prev = i > 0 ? vals[i - 1] : null;
                    const isUp = v !== null && prev !== null && v > prev;
                    const isDown = v !== null && prev !== null && v < prev;

                    return (
                      <td
                        key={i}
                        className={`p-3 text-right font-mono ${
                          isPct
                            ? "text-neutralText"
                            : isHighlight
                            ? "text-neutralText"
                            : "text-neutralText/80"
                        }`}
                      >
                        <span>{fmt(v, row.unit)}</span>
                        {!isPct && v !== null && prev !== null && (
                          <span className={`block text-[9px] ${isUp ? "text-positive" : isDown ? "text-negative" : "text-mutedText"}`}>
                            {isUp ? "▲" : isDown ? "▼" : ""}
                          </span>
                        )}
                      </td>
                    );
                  })}

                  {/* YoY Change Column */}
                  <td className="p-3 text-right">
                    {lastVal !== null && yoyVal !== null ? (
                      <span
                        className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                          lastVal >= yoyVal
                            ? "bg-positive/15 text-positive"
                            : "bg-negative/15 text-negative"
                        }`}
                      >
                        {lastVal >= yoyVal ? (
                          <TrendingUp className="w-2.5 h-2.5" />
                        ) : (
                          <TrendingDown className="w-2.5 h-2.5" />
                        )}
                        {growthPct(lastVal, yoyVal)}
                      </span>
                    ) : (
                      <span className="text-mutedText text-[10px]">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="px-6 py-3 border-t border-border/50 text-[10px] text-mutedText flex items-center gap-1.5">
        <span>All values in ₹ Crores (Consolidated). YoY Chg = same quarter last year comparison.</span>
      </div>
    </div>
  );
}
