"use client";

import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

interface EquityPoint {
  time: string;
  portfolio_value: number;
  benchmark_value: number;
}

interface EquityCurveChartProps {
  data: EquityPoint[];
  initialCapital?: number;
}

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({
  data,
  initialCapital = 100000,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-64 flex items-center justify-center bg-surface/50 border border-border rounded-lg text-mutedText text-sm">
        No equity curve data available. Run a strategy simulation to view performance chart.
      </div>
    );
  }

  // Format Y Axis values in K or Lakhs
  const formatYAxis = (val: number) => {
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
    if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
    return `₹${val}`;
  };

  const formatTooltipValue = (value: number) => [
    `₹${value.toLocaleString("en-IN")}`,
  ];

  return (
    <div className="w-full h-[320px] bg-surface border border-border rounded-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-heading font-semibold text-sm text-neutralText flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-positive inline-block" />
          Strategy Portfolio Performance vs Buy & Hold Benchmark
        </h4>
        <span className="text-xs text-mutedText">Initial: ₹{initialCapital.toLocaleString("en-IN")}</span>
      </div>

      <div className="w-full h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#223028" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="#8FA096"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#223028" }}
              minTickGap={30}
            />
            <YAxis
              stroke="#8FA096"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#223028" }}
              tickFormatter={formatYAxis}
              domain={["auto", "auto"]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#131B18",
                borderColor: "#223028",
                borderRadius: "8px",
                color: "#E6EDEA",
                fontSize: "12px",
              }}
              formatter={formatTooltipValue}
            />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ fontSize: "11px", paddingBottom: "10px" }}
            />
            <Line
              type="monotone"
              dataKey="portfolio_value"
              name="Strategy Portfolio"
              stroke="#2ECC71"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, fill: "#2ECC71" }}
            />
            <Line
              type="monotone"
              dataKey="benchmark_value"
              name="Buy & Hold Benchmark"
              stroke="#C9A227"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
