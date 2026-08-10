"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BarChart2, Loader2, AlertCircle } from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend,
} from "recharts";

interface FinancialBarData {
  year: string;
  Revenue: number | null;
  NetProfit: number | null;
}

function fmtCr(val: number) {
  if (Math.abs(val) >= 100_000) return `${(val / 100_000).toFixed(1)}L Cr`;
  if (Math.abs(val) >= 1_000) return `${(val / 1_000).toFixed(1)}K Cr`;
  return val.toLocaleString("en-IN") + " Cr";
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#131B18", border: "1px solid #223028", borderRadius: 8, padding: "10px 14px", fontSize: 12, color: "#E6EDEA" }}>
      <p style={{ fontWeight: 700, borderBottom: "1px solid #223028", paddingBottom: 4, marginBottom: 6 }}>{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} style={{ display: "flex", justifyContent: "space-between", gap: 24, marginBottom: 3 }}>
          <span style={{ color: p.fill, fontWeight: 500 }}>{p.name}:</span>
          <span style={{ fontFamily: "monospace", fontWeight: 700 }}>
            {p.value !== null && p.value !== undefined ? ("\u20b9" + fmtCr(p.value)) : "N/A"}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function FinancialsBarChart({ ticker }: { ticker: string }) {
  const [chartData, setChartData] = useState<FinancialBarData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await api.get(`/api/companies/${ticker}/financials`);
        if (res?.years && res?.income_statement) {
          const revRow = res.income_statement.find(
            (r: any) => r.metric === "Total Revenue" || r.metric === "Operating Revenue"
          );
          const netRow = res.income_statement.find((r: any) => r.metric === "Net Income");
          const years: string[] = res.years || [];
          const revVals: (number | null)[] = revRow ? revRow.values : [];
          const netVals: (number | null)[] = netRow ? netRow.values : [];
          setChartData(years.map((y, i) => ({
            year: y,
            Revenue: revVals[i] ?? null,
            NetProfit: netVals[i] ?? null,
          })));
        }
      } catch {
        setChartData([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [ticker]);

  if (loading) {
    return (
      <div className="h-36 flex items-center justify-center gap-2 text-mutedText text-xs">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Loading chart…
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="flex items-center gap-2 p-3 bg-bg rounded-lg border border-border/60 text-xs text-mutedText">
        <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        Financial chart unavailable — historical data not accessible from exchange provider.
      </div>
    );
  }

  return (
    <div className="space-y-2 pb-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-neutralText flex items-center gap-1.5">
          <BarChart2 className="w-3.5 h-3.5 text-primary" />
          Revenue &amp; Net Profit — Annual Trend
        </h4>
        <span className="text-[10px] text-mutedText">₹ Crores</span>
      </div>
      <div className="w-full h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 16, left: -8, bottom: 0 }} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="#223028" vertical={false} />
            <XAxis dataKey="year" stroke="#8FA096" tick={{ fontSize: 10 }} tickLine={false} />
            <YAxis stroke="#8FA096" tick={{ fontSize: 10 }} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "6px" }} />
            <Bar dataKey="Revenue" name="Revenue" fill="#2ECC71" fillOpacity={0.85} radius={[3, 3, 0, 0]} maxBarSize={26} />
            <Bar dataKey="NetProfit" name="Net Profit" fill="#3B82F6" fillOpacity={0.85} radius={[3, 3, 0, 0]} maxBarSize={26} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
