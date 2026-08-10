"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { LineChart, Loader2, AlertCircle, TrendingUp, TrendingDown, BarChart3, Table2 } from "lucide-react";
import {
  ResponsiveContainer, LineChart as ReLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from "recharts";

interface RatioRow {
  metric: string;
  values: (number | null)[];
  unit: string;
}

interface RatiosData {
  ticker: string;
  years: string[];
  rows: RatioRow[];
  data_source: string;
  current_pe?: number | null;
  current_pb?: number | null;
  current_div_payout?: number | null;
  message?: string;
}

interface RatioTrendsProps {
  ticker: string;
}

function fmt(val: number | null, unit: string): string {
  if (val === null || val === undefined) return "—";
  if (unit === "%" || unit === "x") return `${val.toFixed(1)}${unit}`;
  return val.toFixed(2);
}

// Render a tiny mini sparkline using a simple SVG bar approach
function Sparkline({ values }: { values: (number | null)[] }) {
  const valid = values.filter((v) => v !== null) as number[];
  if (valid.length < 2) return <span className="text-mutedText text-[10px]">—</span>;

  const min = Math.min(...valid);
  const max = Math.max(...valid);
  const range = max - min || 1;
  const w = 60;
  const h = 20;

  const pts = values
    .map((v, i) => {
      if (v === null) return null;
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .filter(Boolean)
    .join(" ");

  const last = valid[valid.length - 1];
  const first = valid[0];
  const isUp = last >= first;

  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline
        points={pts}
        fill="none"
        stroke={isUp ? "#2ECC71" : "#EF4444"}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

// Colour-code a value: green for good, red for bad (context-dependent)
function valueColor(metric: string, val: number | null): string {
  if (val === null) return "text-mutedText";
  const m = metric.toLowerCase();
  // Higher is better
  if (m.includes("roe") || m.includes("roce") || m.includes("opm") || m.includes("npm") || m.includes("return"))
    return val > 15 ? "text-positive" : val > 8 ? "text-neutralText" : "text-negative";
  // Lower is better
  if (m.includes("debt")) return val < 0.5 ? "text-positive" : val < 1.0 ? "text-neutralText" : "text-negative";
  return "text-neutralText";
}

const ROW_ORDER = [
  "OPM %", "NPM %", "ROE %", "ROCE %", "Return on Assets %",
  "Debt / Equity", "Operating CF Margin %",
  "Revenue CAGR", "Net Profit CAGR",
];

const KEY_CHART_METRICS = ["ROE %", "ROCE %", "OPM %", "NPM %"];
const CHART_COLORS: Record<string, string> = {
  "ROE %": "#2ECC71",
  "ROCE %": "#3B82F6",
  "OPM %": "#F59E0B",
  "NPM %": "#A855F7",
};

export default function RatioTrends({ ticker }: RatioTrendsProps) {
  const [data, setData] = useState<RatiosData | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"table" | "chart">("table");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await api.get<RatiosData>(`/api/companies/${ticker}/ratios`);
        setData(res);
      } catch {
        setData(null);
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
        Computing Historical Ratios…
      </div>
    );
  }

  if (!data || data.data_source === "unavailable" || !data.rows.length) {
    return (
      <div className="border border-border bg-surface rounded-card p-6 space-y-3">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <LineChart className="w-4 h-4 text-primary" />
          Key Ratios (Historical)
        </h3>
        <div className="flex items-start gap-2 p-4 bg-bg rounded-lg border border-border/60 text-xs text-mutedText">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>{data?.message || "Historical ratio data unavailable for this stock."}</span>
        </div>
      </div>
    );
  }

  // Sort rows by preferred order, then any remaining
  const orderedRows = [
    ...ROW_ORDER.map((name) => data.rows.find((r) => r.metric.startsWith(name.split(" ")[0]) && r.metric.includes(name.split(" ")[1] || ""))).filter(Boolean),
    ...data.rows.filter((r) => !ROW_ORDER.some((o) => r.metric.startsWith(o.split(" ")[0]))),
  ] as RatioRow[];

  const uniqueRows = orderedRows.filter(
    (r, i, a) => a.findIndex((x) => x.metric === r.metric) === i
  );

  const years = data.years;
  const displayYears = years.slice(-7); // max 7 years

  return (
    <div className="border border-border bg-surface rounded-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <LineChart className="w-4 h-4 text-primary" />
          Key Ratios
          <span className="text-xs text-mutedText font-normal ml-1">
            ({years.length} years of data)
          </span>
        </h3>
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-bg border border-border rounded-lg overflow-hidden text-xs">
            <button
              onClick={() => setViewMode("table")}
              className={`px-3 py-1.5 flex items-center gap-1.5 transition-colors ${
                viewMode === "table" ? "bg-primary/20 text-primary font-semibold" : "text-mutedText hover:text-neutralText"
              }`}
            >
              <Table2 className="w-3 h-3" /> Table
            </button>
            <button
              onClick={() => setViewMode("chart")}
              className={`px-3 py-1.5 flex items-center gap-1.5 transition-colors ${
                viewMode === "chart" ? "bg-primary/20 text-primary font-semibold" : "text-mutedText hover:text-neutralText"
              }`}
            >
              <BarChart3 className="w-3 h-3" /> Chart
            </button>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-mutedText">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-positive inline-block" /> Good
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-negative inline-block" /> Weak
            </span>
          </div>
        </div>
      </div>

      {/* Current snapshot tiles */}
      <div className="grid grid-cols-3 divide-x divide-border border-b border-border">
        {data.current_pe !== null && data.current_pe !== undefined && (
          <div className="px-5 py-3 text-center">
            <div className="text-[10px] text-mutedText uppercase tracking-wide font-semibold">Current P/E</div>
            <div className="font-heading font-bold text-lg text-neutralText">{data.current_pe?.toFixed(1)}x</div>
          </div>
        )}
        {data.current_pb !== null && data.current_pb !== undefined && (
          <div className="px-5 py-3 text-center">
            <div className="text-[10px] text-mutedText uppercase tracking-wide font-semibold">Current P/B</div>
            <div className="font-heading font-bold text-lg text-neutralText">{data.current_pb?.toFixed(1)}x</div>
          </div>
        )}
        {data.current_div_payout !== null && data.current_div_payout !== undefined && (
          <div className="px-5 py-3 text-center">
            <div className="text-[10px] text-mutedText uppercase tracking-wide font-semibold">Div Payout</div>
            <div className="font-heading font-bold text-lg text-neutralText">{data.current_div_payout?.toFixed(1)}%</div>
          </div>
        )}
      </div>

      {/* Chart view */}
      {viewMode === "chart" && (() => {
        const chartRows = uniqueRows.filter(r => KEY_CHART_METRICS.some(m => r.metric.startsWith(m.split(" ")[0]) && r.metric.includes("%")));
        const chartData = displayYears.map((y, yi) => {
          const pt: any = { year: y };
          chartRows.forEach(r => {
            const v = r.values.slice(-7)[yi];
            pt[r.metric] = v !== null ? Number(v.toFixed(1)) : null;
          });
          return pt;
        });
        return (
          <div className="p-6">
            <div className="w-full h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <ReLineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#223028" vertical={false} />
                  <XAxis dataKey="year" stroke="#8FA096" tick={{ fontSize: 11 }} tickLine={false} />
                  <YAxis stroke="#8FA096" tick={{ fontSize: 11 }} tickLine={false} unit="%" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#131B18", border: "1px solid #223028", borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: "#E6EDEA", fontWeight: 600 }}
                    formatter={(v: any) => [`${v}%`]}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                  {chartRows.map(r => (
                    <Line
                      key={r.metric}
                      type="monotone"
                      dataKey={r.metric}
                      stroke={CHART_COLORS[r.metric] || "#8FA096"}
                      strokeWidth={2}
                      dot={{ r: 3, fill: CHART_COLORS[r.metric] || "#8FA096" }}
                      connectNulls
                    />
                  ))}
                </ReLineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[10px] text-mutedText mt-2">ROE, ROCE, OPM, NPM trend over available annual history. Switch to Table view for full ratio breakdown.</p>
          </div>
        );
      })()}

      {/* Table view */}
      {viewMode === "table" && (
      <div className="overflow-x-auto">
        <table className="w-full text-xs min-w-[600px]">
          <thead>
            <tr className="bg-bg border-b border-border">
              <th className="p-3 text-left font-semibold text-mutedText w-44 sticky left-0 bg-bg z-10">
                Metric
              </th>
              {displayYears.map((y, i) => (
                <th key={i} className="p-3 text-right font-semibold text-mutedText whitespace-nowrap">
                  {y}
                </th>
              ))}
              <th className="p-3 text-right font-semibold text-mutedText">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/40">
            {uniqueRows.map((row, idx) => {
              const vals = row.values.slice(-7);
              const lastVal = vals.filter((v) => v !== null).slice(-1)[0] ?? null;
              const firstVal = vals.filter((v) => v !== null)[0] ?? null;
              const trend = lastVal !== null && firstVal !== null
                ? lastVal > firstVal ? "up" : lastVal < firstVal ? "down" : "flat"
                : "flat";

              const isCagr = row.metric.includes("CAGR");

              return (
                <tr key={idx} className="hover:bg-bg/40 transition-colors">
                  <td className="p-3 text-left font-medium text-mutedText sticky left-0 bg-surface z-10 border-r border-border/40">
                    {row.metric}
                  </td>
                  {vals.map((v, i) => (
                    <td key={i} className={`p-3 text-right font-mono font-semibold ${valueColor(row.metric, v)}`}>
                      {isCagr && i === 0 && v !== null
                        ? <span className="inline-flex items-center gap-1">
                            {trend === "up" ? <TrendingUp className="w-3 h-3 text-positive" /> : <TrendingDown className="w-3 h-3 text-negative" />}
                            {fmt(v, row.unit)}
                          </span>
                        : isCagr && i > 0
                        ? <span className="text-mutedText">—</span>
                        : fmt(v, row.unit)
                      }
                    </td>
                  ))}
                  <td className="p-3 text-right">
                    <div className="flex items-center justify-end">
                      <Sparkline values={vals} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      )}

      <div className="px-6 py-3 border-t border-border/50 text-[10px] text-mutedText">
        Ratios computed from annual financial statements. CAGR = Compounded Annual Growth Rate over available history.
      </div>
    </div>
  );
}
