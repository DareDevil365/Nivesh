"use client";
import { useResource, ResourceState, dateTime } from "@/lib/research";
import { StatementTable, type StatementRow } from "./StatementTable";
export default function QuarterlyResults({ ticker }: { ticker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/quarterly-results`,
  );
  const data = resource.data;
  const sales = data?.rows?.find((r: StatementRow) => r.metric === "Sales");
  const periods: string[] = data?.period_dates || [];
  const growth = sales
    ? periods.map((date, i) => {
        const current = sales.values[i];
        const d = new Date(date);
        const prior = periods.findIndex((other) => {
          const p = new Date(other);
          return (
            p.getUTCFullYear() === d.getUTCFullYear() - 1 &&
            p.getUTCMonth() === d.getUTCMonth()
          );
        });
        const previous = prior < 0 ? null : sales.values[prior];
        return current == null || previous == null || previous === 0
          ? null
          : ((current - previous) / Math.abs(previous)) * 100;
      })
    : [];
  return (
    <ResourceState resource={resource}>
      {data && (
        <div className="space-y-4">
          <h3 className="font-semibold">Quarterly results</h3>
          <p className="text-xs text-mutedText">
            Quarter-end periods from Yahoo Finance. Sales YoY compares matching
            months one year earlier; missing comparisons stay blank. Fetched{" "}
            {dateTime(data.fetched_at)} IST.
          </p>
          <StatementTable
            periods={periods.length ? periods : data.quarters}
            rows={[
              ...(data.rows || []),
              ...(growth.length
                ? [{ metric: "Sales YoY", unit: "%", values: growth }]
                : []),
            ]}
            name={`${ticker}-quarterly`}
          />
        </div>
      )}
    </ResourceState>
  );
}
