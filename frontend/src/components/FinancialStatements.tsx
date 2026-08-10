"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { FileSpreadsheet, TrendingUp, TrendingDown, Loader2, AlertCircle } from "lucide-react";
import FinancialsBarChart from "./FinancialsBarChart";

interface StatementRow {
  metric: string;
  values: (number | null)[];
  unit?: string;
}

interface FinancialsData {
  ticker: string;
  years: string[];
  income_statement: StatementRow[];
  balance_sheet?: StatementRow[];
  cash_flow?: StatementRow[];
  data_source?: string;
  message?: string;
}

interface FinancialStatementsProps {
  ticker: string;
}

function fmtCr(val: number | null): string {
  if (val === null || val === undefined) return "—";
  const abs = Math.abs(val);
  const sign = val < 0 ? "-" : "";
  if (abs >= 100_000) return `${sign}₹${(abs / 100_000).toFixed(1)}L Cr`;
  if (abs >= 1_000) return `${sign}₹${(abs / 1_000).toFixed(1)}K Cr`;
  return `${sign}₹${abs.toLocaleString("en-IN")} Cr`;
}

function yoyBadge(curr: number | null, prev: number | null) {
  if (curr === null || prev === null || prev === 0) return null;
  const pct = ((curr - prev) / Math.abs(prev)) * 100;
  const isPos = pct >= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 ml-1 px-1 py-0.5 rounded text-[9px] font-semibold ${
        isPos ? "bg-positive/15 text-positive" : "bg-negative/15 text-negative"
      }`}
    >
      {isPos ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
      {isPos ? "+" : ""}
      {pct.toFixed(1)}%
    </span>
  );
}

// Which rows to highlight bold
const HIGHLIGHT = new Set([
  "Total Revenue", "Operating Revenue",
  "Operating Income", "EBITDA",
  "Net Income", "Total Equity", "Total Assets", "Operating Cash Flow", "Free Cash Flow",
]);

export const FinancialStatements: React.FC<FinancialStatementsProps> = ({ ticker }) => {
  const [data, setData] = useState<FinancialsData | null>(null);
  const [activeTab, setActiveTab] = useState<"income" | "balance" | "cash">("income");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadFinancials() {
      setLoading(true);
      try {
        const res = await api.get<FinancialsData>(`/api/companies/${ticker}/financials`);
        setData(res);
      } catch (err) {
        console.error("Failed to load financials", err);
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    loadFinancials();
  }, [ticker]);

  if (loading) {
    return (
      <div className="w-full h-48 border border-border bg-surface rounded-card flex items-center justify-center text-mutedText text-sm gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        <span>Loading Financial Statements…</span>
      </div>
    );
  }

  const unavailable = !data || data.data_source === "unavailable" || (
    !data.income_statement?.length && !data.balance_sheet?.length && !data.cash_flow?.length
  );

  if (unavailable) {
    return (
      <div className="border border-border bg-surface rounded-card p-6 space-y-3">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <FileSpreadsheet className="w-4 h-4 text-primary" />
          Financial Statements
        </h3>
        <div className="flex items-start gap-2 p-4 bg-bg rounded-lg border border-border/60 text-xs text-mutedText">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>{data?.message || "Financial statement data is not available for this stock from the current data source."}</span>
        </div>
      </div>
    );
  }

  const currentRows =
    activeTab === "income"
      ? data!.income_statement
      : activeTab === "balance"
      ? data!.balance_sheet || []
      : data!.cash_flow || [];

  const years = data!.years;

  return (
    <div className="border border-border bg-surface rounded-card overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-6 py-4 border-b border-border">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <FileSpreadsheet className="w-4 h-4 text-primary" />
          Financial Statements
          <span className="text-xs text-mutedText font-normal ml-1">
            ({years.length} years · ₹ Crores)
          </span>
        </h3>

        <div className="flex items-center gap-1 bg-bg p-1 rounded-lg border border-border">
          {(["income", "balance", "cash"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                activeTab === tab
                  ? "bg-primary text-white"
                  : "text-mutedText hover:text-neutralText"
              }`}
            >
              {tab === "income" ? "P&L" : tab === "balance" ? "Balance Sheet" : "Cash Flow"}
            </button>
          ))}
        </div>
      </div>

      {/* Revenue & Net Profit bar chart — only on income tab */}
      {activeTab === "income" && (
        <div className="px-6 pt-4">
          <FinancialsBarChart ticker={ticker} />
        </div>
      )}

      {/* Table */}
      {currentRows.length === 0 ? (
        <div className="p-8 text-center text-xs text-mutedText">
          No data available for this statement type.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[650px]">
            <thead className="bg-bg border-b border-border">
              <tr>
                <th className="p-3 font-semibold text-mutedText sticky left-0 bg-bg z-10 w-44">Metric</th>
                {years.map((y, idx) => (
                  <th key={idx} className="p-3 font-mono text-right text-mutedText whitespace-nowrap">
                    {y}
                  </th>
                ))}
                <th className="p-3 text-right text-mutedText whitespace-nowrap">3yr Trend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {currentRows.map((row, idx) => {
                const isHighlight = HIGHLIGHT.has(row.metric);
                const firstNonNull = row.values.find((v) => v !== null);
                const lastNonNull = [...row.values].reverse().find((v) => v !== null);

                const threeyearPct =
                  firstNonNull != null && lastNonNull != null && firstNonNull !== 0
                    ? (((lastNonNull - firstNonNull) / Math.abs(firstNonNull)) * 100).toFixed(1)
                    : null;

                return (
                  <tr
                    key={idx}
                    className={`hover:bg-bg/40 transition-colors ${isHighlight ? "bg-bg/10" : ""}`}
                  >
                    <td
                      className={`p-3 sticky left-0 z-10 ${
                        isHighlight
                          ? "font-semibold text-neutralText bg-surface border-r border-border/40"
                          : "font-medium text-mutedText bg-surface border-r border-border/40"
                      }`}
                    >
                      {row.metric}
                    </td>
                    {row.values.map((v, vIdx) => {
                      const prev = vIdx > 0 ? row.values[vIdx - 1] : null;
                      return (
                        <td
                          key={vIdx}
                          className={`p-3 text-right ${
                            isHighlight ? "font-semibold text-neutralText" : "text-neutralText/80"
                          }`}
                        >
                          <span className="font-mono">{fmtCr(v)}</span>
                          {isHighlight && vIdx > 0 && yoyBadge(v, prev)}
                        </td>
                      );
                    })}
                    <td className="p-3 text-right">
                      {threeyearPct !== null ? (
                        <span
                          className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            parseFloat(threeyearPct) >= 0
                              ? "bg-positive/20 text-positive"
                              : "bg-negative/20 text-negative"
                          }`}
                        >
                          {parseFloat(threeyearPct) >= 0 ? (
                            <TrendingUp className="w-3 h-3" />
                          ) : (
                            <TrendingDown className="w-3 h-3" />
                          )}
                          {parseFloat(threeyearPct) >= 0 ? "+" : ""}
                          {threeyearPct}%
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
      )}

      <div className="px-6 py-3 border-t border-border/50 text-[10px] text-mutedText">
        All figures in ₹ Crores. Consolidated financial statements. YoY badge shown for key rows.
      </div>
    </div>
  );
};
