"use client";
import { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { useResource, ResourceState } from "@/lib/research";
import { StatementTable, type StatementRow } from "./StatementTable";
export default function RatioTrends({ ticker }: { ticker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/ratios`,
  );
  const [selected, setSelected] = useState("ROE %");
  const data = resource.data;
  const row: StatementRow | undefined =
    data?.rows?.find((r: StatementRow) => r.metric === selected) ||
    data?.rows?.[0];
  return (
    <ResourceState resource={resource}>
      {data && (
        <div className="space-y-5">
          <h3 className="font-semibold">Financial ratio trends</h3>
          <p className="text-xs text-mutedText">{data.methodology}</p>
          {row && (
            <>
              <label className="text-sm">
                Chart metric
                <select
                  aria-label="Chart metric"
                  value={row.metric}
                  onChange={(e) => setSelected(e.target.value)}
                  className="ml-3 bg-bg border border-border rounded-lg p-2 text-xs"
                >
                  {data.rows.map((r: StatementRow) => (
                    <option key={r.metric}>{r.metric}</option>
                  ))}
                </select>
              </label>
              <div className="h-64 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={data.years.map((year: string, i: number) => ({
                      year,
                      value: row.values[i],
                    }))}
                  >
                    <CartesianGrid stroke="#223028" />
                    <XAxis
                      dataKey="year"
                      stroke="#8FA096"
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      stroke="#8FA096"
                      unit={row.unit}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#131B18",
                        borderColor: "#223028",
                      }}
                    />
                    <Line
                      type="linear"
                      dataKey="value"
                      name={row.metric}
                      stroke="#2ECC71"
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
          <StatementTable
            periods={data.years}
            rows={data.rows || []}
            name={`${ticker}-ratios`}
          />
        </div>
      )}
    </ResourceState>
  );
}
