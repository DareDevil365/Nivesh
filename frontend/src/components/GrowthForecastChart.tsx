"use client";
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
import { useResource, ResourceState, number } from "@/lib/research";
import type { StatementRow } from "./StatementTable";
export default function GrowthForecastChart({ ticker }: { ticker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/financials`,
  );
  const data = resource.data;
  const revenue: StatementRow | undefined = data?.income_statement?.find(
    (r: StatementRow) => r.metric === "Total Revenue",
  );
  const earnings: StatementRow | undefined = data?.income_statement?.find(
    (r: StatementRow) => r.metric === "Net Income",
  );
  const cagr = (row?: StatementRow) => {
    if (!row || row.values.length < 2) return null;
    const first = row.values[0],
      last = row.values[row.values.length - 1];
    const dates = data?.period_dates || [];
    const years =
      dates.length >= 2
        ? (new Date(dates[dates.length - 1]).getTime() -
            new Date(dates[0]).getTime()) /
          (365.25 * 86400000)
        : 0;
    return first != null && first > 0 && last != null && last > 0 && years > 0
      ? ((last / first) ** (1 / years) - 1) * 100
      : null;
  };
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="space-y-4">
          <h3 className="font-semibold">Reported revenue & earnings history</h3>
          <p className="text-xs text-mutedText">
            Observed annual statements, without generated forecasts. Endpoint
            CAGR uses actual elapsed dates and is unavailable when either
            endpoint is missing or non-positive.
          </p>
          <div className="flex flex-wrap gap-6 text-sm">
            <span>Revenue CAGR: {number(cagr(revenue), "%")}</span>
            <span>Net income CAGR: {number(cagr(earnings), "%")}</span>
          </div>
          {data.years.length > 0 && (
            <div className="h-72 min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={data.years.map((year: string, i: number) => ({
                    year,
                    revenue: revenue?.values[i],
                    earnings: earnings?.values[i],
                  }))}
                >
                  <CartesianGrid stroke="#223028" />
                  <XAxis dataKey="year" stroke="#8FA096" />
                  <YAxis stroke="#8FA096" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#131B18",
                      borderColor: "#223028",
                    }}
                  />
                  <Legend />
                  <Line
                    type="linear"
                    dataKey="revenue"
                    name="Revenue (₹ Cr)"
                    stroke="#2ECC71"
                    connectNulls={false}
                  />
                  <Line
                    type="linear"
                    dataKey="earnings"
                    name="Net income (₹ Cr)"
                    stroke="#C9A227"
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
      )}
    </ResourceState>
  );
}
