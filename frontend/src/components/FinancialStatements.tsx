"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { FileSpreadsheet, TrendingUp, Loader2 } from "lucide-react";

interface StatementRow {
  metric: string;
  values: number[];
}

interface FinancialsData {
  ticker: string;
  years: string[];
  income_statement: StatementRow[];
  balance_sheet?: StatementRow[];
  cash_flow?: StatementRow[];
}

interface FinancialStatementsProps {
  ticker: string;
}

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
        <span>Loading 5-Year Financial Statements...</span>
      </div>
    );
  }

  if (!data) return null;

  const currentRows =
    activeTab === "income"
      ? data.income_statement
      : activeTab === "balance"
      ? data.balance_sheet || []
      : data.cash_flow || [];

  return (
    <div className="border border-border bg-surface rounded-card p-6 space-y-4">
      {/* Component Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-3">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <FileSpreadsheet className="w-4 h-4 text-primary" />
          5-Year Historical Financial Statements
        </h3>

        <div className="flex items-center gap-1 bg-bg p-1 rounded-lg border border-border">
          <button
            onClick={() => setActiveTab("income")}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
              activeTab === "income" ? "bg-primary text-neutralText" : "text-mutedText hover:text-neutralText"
            }`}
          >
            Income Statement
          </button>
          <button
            onClick={() => setActiveTab("balance")}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
              activeTab === "balance" ? "bg-primary text-neutralText" : "text-mutedText hover:text-neutralText"
            }`}
          >
            Balance Sheet
          </button>
          <button
            onClick={() => setActiveTab("cash")}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
              activeTab === "cash" ? "bg-primary text-neutralText" : "text-mutedText hover:text-neutralText"
            }`}
          >
            Cash Flow
          </button>
        </div>
      </div>

      {/* Financial Statement Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs min-w-[650px]">
          <thead className="bg-bg text-mutedText border-b border-border">
            <tr>
              <th className="p-3 font-semibold text-neutralText">Metric</th>
              {data.years.map((y, idx) => (
                <th key={idx} className="p-3 font-mono text-right">{y}</th>
              ))}
              <th className="p-3 text-right">YoY Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {currentRows.map((row, idx) => {
              const firstVal = row.values[0] || 1;
              const lastVal = row.values[row.values.length - 1] || 1;
              const yoyPct = (((lastVal - firstVal) / Math.abs(firstVal)) * 100).toFixed(1);

              return (
                <tr key={idx} className="hover:bg-bg/40 transition-colors">
                  <td className="p-3 font-medium text-neutralText">{row.metric}</td>
                  {row.values.map((v, vIdx) => (
                    <td key={vIdx} className="p-3 font-mono text-right text-neutralText/90">
                      ₹{v.toLocaleString("en-IN")}
                    </td>
                  ))}
                  <td className="p-3 text-right">
                    <span
                      className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                        parseFloat(yoyPct) >= 0
                          ? "bg-positive/20 text-positive"
                          : "bg-negative/20 text-negative"
                      }`}
                    >
                      <TrendingUp className="w-3 h-3" />
                      {parseFloat(yoyPct) >= 0 ? "+" : ""}{yoyPct}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
