"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TrendingUp, Sparkles, Loader2, AlertCircle } from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

interface GrowthData {
  years: string[];
  revenue: (number | null)[];
  earnings: (number | null)[];
  annual_revenue_growth_pct?: number | null;
  annual_earnings_growth_pct?: number | null;
}

interface GrowthForecastChartProps {
  ticker: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#131B18] border border-[#223028] rounded-lg p-3 text-xs text-neutralText space-y-1 shadow-lg">
      <p className="font-bold border-b border-[#223028] pb-1 mb-1">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4">
          <span style={{ color: p.color }} className="font-medium">
            {p.name}:
          </span>
          <span className="font-mono font-bold">
            {p.value !== null ? `₹${p.value.toLocaleString("en-IN")} Cr` : "—"}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function GrowthForecastChart({ ticker }: GrowthForecastChartProps) {
  const [data, setData] = useState<GrowthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const finRes = await api.get(`/api/companies/${ticker}/financials`);

        if (finRes && finRes.years && finRes.income_statement) {
          const revRow = finRes.income_statement.find(
            (r: any) => r.metric === "Total Revenue" || r.metric === "Operating Revenue"
          );
          const netRow = finRes.income_statement.find(
            (r: any) => r.metric === "Net Income"
          );

          const years = finRes.years || [];
          const revVals = revRow ? revRow.values : [];
          const netVals = netRow ? netRow.values : [];

          // Compute historical CAGRs
          let revCagr: number | null = null;
          let netCagr: number | null = null;

          const validRev = revVals.filter((v: any) => v !== null && v > 0);
          if (validRev.length >= 2) {
            const start = validRev[0];
            const end = validRev[validRev.length - 1];
            const n = validRev.length - 1;
            revCagr = round2(((end / start) ** (1 / n) - 1) * 100);
          }

          const validNet = netVals.filter((v: any) => v !== null && v > 0);
          if (validNet.length >= 2) {
            const start = validNet[0];
            const end = validNet[validNet.length - 1];
            const n = validNet.length - 1;
            netCagr = round2(((end / start) ** (1 / n) - 1) * 100);
          }

          setData({
            years,
            revenue: revVals,
            earnings: netVals,
            annual_revenue_growth_pct: revCagr,
            annual_earnings_growth_pct: netCagr,
          });
        }
      } catch (e) {
        console.error("Failed to load growth data", e);
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [ticker]);

  function round2(val: number) {
    return Math.round(val * 10) / 10;
  }

  if (loading) {
    return (
      <div className="border border-border bg-surface rounded-card p-6 flex items-center justify-center gap-2 h-48 text-mutedText text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Loading Growth Trajectory…
      </div>
    );
  }

  if (!data || !data.years || data.years.length === 0) {
    return (
      <div className="border border-border bg-surface rounded-card p-6 space-y-3">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" />
          Earnings & Revenue Growth Trajectory
        </h3>
        <div className="flex items-start gap-2 p-4 bg-bg rounded-lg border border-border/60 text-xs text-mutedText">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>Growth data is unavailable for this stock.</span>
        </div>
      </div>
    );
  }

  // Combine historical data for chart
  const chartData = data.years.map((y, i) => ({
    year: y,
    Revenue: data.revenue[i] ?? null,
    Earnings: data.earnings[i] ?? null,
  }));

  // Only project forecast if CAGR is known
  const companyRevG = data.annual_revenue_growth_pct ?? null;
  const companyNetG = data.annual_earnings_growth_pct ?? null;
  const lastYear = data.years[data.years.length - 1];
  const lastRev = data.revenue[data.revenue.length - 1] ?? 0;
  const lastNet = data.earnings[data.earnings.length - 1] ?? 0;

  const currentFY = new Date().getMonth() >= 3
    ? new Date().getFullYear() - 1999  // Apr–Dec: FY is current year - 2000 + 1
    : new Date().getFullYear() - 2000;  // Jan–Mar: FY hasn't turned yet

  let isForecastStale = false;
  if (lastRev > 0 && companyRevG !== null) {
    const revGrowth = companyRevG / 100;
    const netGrowth = (companyNetG ?? companyRevG) / 100;
    const yrNum = parseInt(lastYear.replace("FY", "")) || currentFY;
    isForecastStale = yrNum + 1 < currentFY; // forecast year already passed
    const f1Year = `FY${(yrNum + 1).toString().padStart(2, "0")} (Est)`;
    const f2Year = `FY${(yrNum + 2).toString().padStart(2, "0")} (Est)`;

    const f1Rev = Math.round(lastRev * (1 + revGrowth));
    const f2Rev = Math.round(f1Rev * (1 + revGrowth));
    const f1Net = lastNet > 0 ? Math.round(lastNet * (1 + netGrowth)) : null;
    const f2Net = f1Net !== null ? Math.round(f1Net * (1 + netGrowth)) : null;

    chartData.push({ year: f1Year, Revenue: f1Rev, Earnings: f1Net });
    chartData.push({ year: f2Year, Revenue: f2Rev, Earnings: f2Net });
  }

  return (
    <div className="border border-border bg-surface rounded-card overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-6 py-4 border-b border-border">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-primary" />
          Revenue & Earnings Growth Trajectory
        </h3>
        <span className="text-xs px-2.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-semibold">
          Institutional Growth Projection
        </span>
      </div>

      {/* Benchmark comparison bars */}
      <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border border-b border-border">
        <div className="p-4 space-y-1.5 text-center">
          <div className="text-[10px] text-mutedText uppercase font-semibold">Revenue CAGR (Historical)</div>
          <div className="font-heading font-bold text-xl text-positive">
            {companyRevG != null ? (companyRevG > 0 ? `+${companyRevG}%` : `${companyRevG}%`) : "N/A"}
          </div>
          <div className="text-[10px] text-mutedText">
            Compound annual growth rate from financials
          </div>
        </div>

        <div className="p-4 space-y-1.5 text-center">
          <div className="text-[10px] text-mutedText uppercase font-semibold">Earnings CAGR (Historical)</div>
          <div className="font-heading font-bold text-xl text-secondary">
            {companyNetG != null ? (companyNetG > 0 ? `+${companyNetG}%` : `${companyNetG}%`) : "N/A"}
          </div>
          <div className="text-[10px] text-mutedText">
            Net profit compound annual growth rate
          </div>
        </div>

        <div className="p-4 space-y-1.5 text-center">
          <div className="text-[10px] text-mutedText uppercase font-semibold">Revenue vs Earnings</div>
          <div className="font-heading font-bold text-xl text-neutralText flex items-center justify-center gap-1">
            <Sparkles className="w-4 h-4 text-amber-400" />
            {companyRevG != null && companyNetG != null
              ? companyNetG > companyRevG ? "Margin Expanding" : companyRevG > companyNetG ? "Revenue Growing Faster" : "Even Growth"
              : "Data Limited"
            }
          </div>
          <div className="text-[10px] text-mutedText font-semibold">
            {companyRevG != null && companyNetG != null
              ? companyNetG > companyRevG
                ? `Earnings grow faster by +${(companyNetG - companyRevG).toFixed(1)}%`
                : companyRevG > companyNetG
                ? `Revenue grows faster by +${(companyRevG - companyNetG).toFixed(1)}%`
                : "Revenue and earnings growing at same pace"
              : "Based on available financial data"
            }
          </div>
        </div>
      </div>

      {/* Stale forecast warning */}
      {isForecastStale && (
        <div className="mx-6 mb-0 mt-3 flex items-start gap-2 p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-lg text-[11px] text-amber-400">
          <span className="font-semibold shrink-0">⚠ Note:</span>
          <span>Financial data may be up to 1–2 years old. Estimate projections shown may overlap with actual reported quarters. Verify against latest exchange filings.</span>
        </div>
      )}

      {/* Chart */}
      <div className="p-6">
        <div className="w-full h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2ECC71" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#2ECC71" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorEarn" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#223028" vertical={false} />
              <XAxis dataKey="year" stroke="#8FA096" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis stroke="#8FA096" tick={{ fontSize: 11 }} tickLine={false} unit=" Cr" />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
              <Area
                type="monotone"
                dataKey="Revenue"
                stroke="#2ECC71"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorRev)"
              />
              <Area
                type="monotone"
                dataKey="Earnings"
                stroke="#3B82F6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorEarn)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="px-6 py-2.5 border-t border-border/50 text-[10px] text-mutedText flex items-center justify-between">
        <span>Historical financials in ₹ Crores. Estimates extrapolated from historical CAGR — not analyst forecasts. Source: Exchange data via yfinance.</span>
        <span className="text-amber-400 shrink-0 ml-2">Exchange data · No AI estimates</span>
      </div>
    </div>
  );
}
