"use client";
import { useState } from "react";
import { useResource, ResourceState, dateTime } from "@/lib/research";
import { StatementTable } from "./StatementTable";
export function FinancialStatements({ ticker }: { ticker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/financials`,
  );
  const [mode, setMode] = useState("income_statement");
  const data = resource.data;
  return (
    <ResourceState resource={resource}>
      {data && (
        <div className="space-y-4">
          <h3 className="font-semibold">Annual financial statements</h3>
          <p className="text-xs text-mutedText">
            {data.basis} Monetary amounts are in crores; EPS is rupees per share
            and share counts are units. Periods are aligned by fiscal end date.
            Fetched: {dateTime(data.fetched_at)} IST.
          </p>
          <div className="flex flex-wrap gap-2">
            {[
              ["income_statement", "Profit & loss"],
              ["balance_sheet", "Balance sheet"],
              ["cash_flow", "Cash flow"],
            ].map(([key, label]) => (
              <button
                key={key}
                onClick={() => setMode(key)}
                className={`rounded-lg border px-4 py-2 text-xs ${mode === key ? "border-primary text-primary" : "border-border text-mutedText"}`}
              >
                {label}
              </button>
            ))}
          </div>
          <StatementTable
            periods={data.period_dates?.length ? data.period_dates : data.years}
            rows={data[mode] || []}
            name={`${ticker}-${mode}`}
          />
        </div>
      )}
    </ResourceState>
  );
}
