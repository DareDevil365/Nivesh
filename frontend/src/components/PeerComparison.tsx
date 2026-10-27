"use client";
import { useState } from "react";
import Link from "next/link";
import {
  useResource,
  ResourceState,
  EmptyState,
  CoverageNote,
  number,
  download,
  csvCell,
} from "@/lib/research";
export function PeerComparison({ currentTicker }: { currentTicker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(currentTicker)}/peers`,
  );
  const [sort, setSort] = useState("market_cap");
  const data = resource.data;
  const peers = [...(data?.peers || [])].sort((a, b) =>
    a[sort] == null ? 1 : b[sort] == null ? -1 : b[sort] - a[sort],
  );
  const exportCsv = () =>
    download(
      `${currentTicker}-peers.csv`,
      [
        [
          "Ticker",
          "Company",
          "Market cap INR",
          "P/E",
          "P/B",
          "ROE %",
          "ROCE %",
          "D/E",
          "Fetched at",
        ],
        ...peers.map((p) => [
          p.ticker,
          p.name,
          p.market_cap,
          p.pe,
          p.pb,
          p.roe,
          p.roce,
          p.debt_equity,
          p.fetched_at,
        ]),
      ]
        .map((r) => r.map(csvCell).join(","))
        .join("\n"),
      "text/csv",
    );
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-semibold">Industry peer comparison</h3>
            <div className="flex gap-2">
              <select
                aria-label="Sort peers"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                className="bg-bg border border-border p-2 rounded-lg text-xs"
              >
                {[
                  ["market_cap", "Market cap"],
                  ["roe", "ROE"],
                  ["roce", "ROCE"],
                  ["pe", "P/E"],
                ].map(([key, label]) => (
                  <option key={key} value={key}>
                    {label} ↓
                  </option>
                ))}
              </select>
              <button
                onClick={exportCsv}
                className="text-xs text-primary border border-border rounded-lg p-2"
              >
                Export
              </button>
              <button
                onClick={resource.reload}
                className="text-xs border border-border rounded-lg p-2"
              >
                Reload peers
              </button>
            </div>
          </div>
          <p className="text-xs text-mutedText">
            {data.basis} Missing values sort last. Current company is
            highlighted.
          </p>
          <CoverageNote coverage={data.coverage} />
          {peers.length <= 1 && (
            <EmptyState title="No comparable peers in the current snapshot">
              Refresh the market snapshot in the screener, then reload this
              comparison. Unrelated companies are not substituted.
            </EmptyState>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[650px] text-left">
              <thead>
                <tr className="text-mutedText">
                  <th className="p-3">Company</th>
                  {[
                    "Market cap (₹ Cr)",
                    "P/E",
                    "P/B",
                    "ROE",
                    "ROCE",
                    "D/E",
                  ].map((k) => (
                    <th key={k} className="p-3 text-right">
                      {k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {peers.map((p) => (
                  <tr
                    key={p.ticker}
                    className={`border-t border-border ${p.ticker === currentTicker ? "bg-primary/10" : ""}`}
                  >
                    <td className="p-3">
                      <Link
                        className="hover:text-primary"
                        href={`/stock/${p.ticker}`}
                      >
                        {p.name}
                      </Link>
                    </td>
                    {[
                      p.market_cap_cr,
                      p.pe,
                      p.pb,
                      p.roe,
                      p.roce,
                      p.debt_equity,
                    ].map((v, i) => (
                      <td key={i} className="p-3 text-right">
                        {number(v, i === 3 || i === 4 ? "%" : "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </ResourceState>
  );
}
