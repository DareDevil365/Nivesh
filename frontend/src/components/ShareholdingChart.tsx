"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Users, Loader2, AlertCircle, ExternalLink } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Cell,
} from "recharts";

interface ShareholdingCategory {
  category: string;
  key: string;
  pct: number;
  trend: number[];
  color: string;
}

interface ShareholdingData {
  ticker: string;
  quarters: string[];
  breakdown: ShareholdingCategory[];
  pledged_pct: number | null;
  data_source: string;
  message?: string;
  note?: string;
  fii_dii_estimated?: boolean;
}

interface ShareholdingChartProps {
  ticker: string;
}

// Fixed colors per category
const CATEGORY_COLORS: Record<string, string> = {
  Promoter: "#2ECC71",
  FII: "#3B82F6",
  DII: "#9333EA",
  "Public & Others": "#8FA096",
  "Promoter & Insiders": "#2ECC71",
  "Institutional Holdings": "#3B82F6",
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        backgroundColor: "#131B18",
        border: "1px solid #223028",
        borderRadius: 8,
        padding: "10px 14px",
        fontSize: 12,
        color: "#E6EDEA",
      }}
    >
      <p style={{ fontWeight: 600, marginBottom: 6 }}>{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.fill, margin: "2px 0" }}>
          {p.dataKey}: {p.value?.toFixed(1)}%
        </p>
      ))}
    </div>
  );
};

export const ShareholdingChart: React.FC<ShareholdingChartProps> = ({ ticker }) => {
  const [data, setData] = useState<ShareholdingData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadShareholding() {
      setLoading(true);
      try {
        const res = await api.get<ShareholdingData>(`/api/companies/${ticker}/shareholding`);
        setData(res);
      } catch (err) {
        console.error("Failed to load shareholding", err);
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    loadShareholding();
  }, [ticker]);

  if (loading) {
    return (
      <div className="w-full h-48 border border-border bg-surface rounded-card flex items-center justify-center text-mutedText text-sm gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        <span>Loading Shareholding Pattern…</span>
      </div>
    );
  }

  // Unavailable state — show helpful link to NSE
  if (!data || data.data_source === "unavailable" || !data.breakdown?.length) {
    const symbol = ticker.replace(".NS", "").replace(".BO", "");
    return (
      <div className="border border-border bg-surface rounded-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" />
            Shareholding Pattern
          </h3>
        </div>
        <div className="flex items-start gap-2 p-4 bg-bg rounded-lg border border-border/60 text-xs text-mutedText">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-2">
            <p>{data?.message || "Shareholding pattern data is unavailable from the current data source."}</p>
            <a
              href={`https://www.nseindia.com/get-quotes/equity?symbol=${symbol}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline font-semibold"
            >
              View on NSE India <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Build chart data — one object per quarter
  const chartData = data.quarters.map((q, qIdx) => {
    const item: any = { quarter: q };
    data.breakdown.forEach((b) => {
      item[b.category] = b.trend[qIdx] !== undefined ? b.trend[qIdx] : b.pct;
    });
    return item;
  });

  // Pie-style summary tiles for current snapshot
  const latest = data.breakdown.map((b) => ({
    ...b,
    current: b.trend[b.trend.length - 1] ?? b.pct,
  }));

  return (
    <div className="border border-border bg-surface rounded-card overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-6 py-4 border-b border-border">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <Users className="w-4 h-4 text-primary" />
          Shareholding Pattern
        </h3>

        {data.pledged_pct != null && data.pledged_pct > 0 ? (
          <span className="text-xs px-2.5 py-0.5 rounded bg-negative/20 text-negative border border-negative/30 font-medium">
            Promoter Pledged: {data.pledged_pct}%
          </span>
        ) : (
          <span className="text-xs px-2.5 py-0.5 rounded bg-positive/20 text-positive border border-positive/30 font-medium">
            Zero Promoter Pledge
          </span>
        )}
      </div>

      {/* Latest Snapshot Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 divide-x divide-border border-b border-border">
        {latest.map((b) => (
          <div key={b.category} className="px-4 py-3 text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <span
                className="w-2.5 h-2.5 rounded-full inline-block flex-shrink-0"
                style={{ backgroundColor: CATEGORY_COLORS[b.category] || b.color }}
              />
              <span className="text-[10px] text-mutedText font-semibold uppercase tracking-wide">
                {b.category}
              </span>
            </div>
            <div className="font-heading font-bold text-lg text-neutralText">
              {b.current.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>

      {/* Stacked Bar Chart */}
      <div className="w-full h-[200px] px-2 py-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 16, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#223028" vertical={false} />
            <XAxis
              dataKey="quarter"
              stroke="#8FA096"
              tick={{ fontSize: 11 }}
              tickLine={false}
            />
            <YAxis
              stroke="#8FA096"
              tick={{ fontSize: 11 }}
              tickLine={false}
              domain={[0, 100]}
              unit="%"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
            {data.breakdown.map((b) => (
              <Bar
                key={b.category}
                dataKey={b.category}
                stackId="a"
                fill={CATEGORY_COLORS[b.category] || b.color}
                radius={b.category === data.breakdown[data.breakdown.length - 1].category ? [4, 4, 0, 0] : [0, 0, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* FII/DII Estimated Split Warning */}
      {data.fii_dii_estimated && (
        <div className="mx-6 mb-3 mt-2 flex items-start gap-2 p-3 bg-amber-500/10 border border-amber-500/25 rounded-lg text-[11px] text-amber-300">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
          <span>
            <span className="font-semibold">Estimated Split:</span> FII and DII figures are a 50/50 approximation of total institutional holdings — official quarterly breakdown is not available from this data source.
            {" "}
            <a
              href={`https://www.nseindia.com/get-quotes/equity?symbol=${ticker.replace(".NS","").replace(".BO","")}`}
              target="_blank" rel="noreferrer"
              className="underline font-semibold hover:text-amber-200 transition-colors"
            >
              View NSE Official Data →
            </a>
          </span>
        </div>
      )}

      {/* Older general note if any */}
      {data.note && !data.fii_dii_estimated && (
        <div className="px-6 py-2 border-t border-border/50 text-[10px] text-mutedText flex items-center gap-1">
          <AlertCircle className="w-3 h-3 text-amber-400 flex-shrink-0" />
          {data.note}
        </div>
      )}
    </div>
  );
};
