"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Users, Loader2 } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

interface ShareholdingData {
  ticker: string;
  quarters: string[];
  breakdown: Array<{
    category: string;
    pct: number;
    trend: number[];
  }>;
  pledged_pct: number;
}

interface ShareholdingChartProps {
  ticker: string;
}

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
        <span>Loading Shareholding Pattern...</span>
      </div>
    );
  }

  if (!data) return null;

  // Format data for Recharts stacked bar chart across quarters
  const chartData = data.quarters.map((q, qIdx) => {
    const item: any = { quarter: q };
    data.breakdown.forEach((b) => {
      item[b.category] = b.trend[qIdx] || b.pct;
    });
    return item;
  });

  return (
    <div className="border border-border bg-surface rounded-card p-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <Users className="w-4 h-4 text-primary" />
          Shareholding Pattern (Promoter, FII, DII, Public)
        </h3>

        {data.pledged_pct > 0 ? (
          <span className="text-xs px-2.5 py-0.5 rounded bg-negative/20 text-negative border border-negative/30 font-medium">
            Promoter Pledged: {data.pledged_pct}%
          </span>
        ) : (
          <span className="text-xs px-2.5 py-0.5 rounded bg-positive/20 text-positive border border-positive/30 font-medium">
            Zero Promoter Pledge
          </span>
        )}
      </div>

      <div className="w-full h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#223028" vertical={false} />
            <XAxis dataKey="quarter" stroke="#8FA096" tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis stroke="#8FA096" tick={{ fontSize: 11 }} tickLine={false} domain={[0, 100]} unit="%" />
            <Tooltip
              contentStyle={{
                backgroundColor: "#131B18",
                borderColor: "#223028",
                borderRadius: "8px",
                color: "#E6EDEA",
                fontSize: "12px",
              }}
              formatter={(val: number) => [`${val}%`]}
            />
            <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
            <Bar dataKey="Promoter" stackId="a" fill="#2ECC71" />
            <Bar dataKey="FII" stackId="a" fill="#3B82F6" />
            <Bar dataKey="DII" stackId="a" fill="#9333EA" />
            <Bar dataKey="Public & Others" stackId="a" fill="#8FA096" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
