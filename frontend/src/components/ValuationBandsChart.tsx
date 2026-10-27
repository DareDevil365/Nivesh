"use client";
import { useState } from "react";
import { useResource, ResourceState, EmptyState, number } from "@/lib/research";
export default function ValuationBandsChart({ ticker }: { ticker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/valuation-bands`,
  );
  const [mode, setMode] = useState<"pe" | "pb">("pe");
  const data = resource.data;
  const bands = data?.[`${mode}_bands`];
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="rounded-card border border-border p-5 space-y-4">
          <h3 className="font-semibold">
            Retrospective annual valuation comparison
          </h3>
          <div className="flex gap-2">
            {(["pe", "pb"] as const).map((k) => (
              <button
                key={k}
                onClick={() => setMode(k)}
                className={`rounded-lg border px-4 py-2 text-xs ${mode === k ? "border-primary text-primary" : "border-border text-mutedText"}`}
              >
                {k === "pe" ? "P/E" : "P/B"}
              </button>
            ))}
          </div>
          {bands ? (
            <>
              <p className="text-xs text-mutedText">
                {bands.sample_count} annual observations. Current:{" "}
                {number(bands.current, "x")}; sample median:{" "}
                {number(bands.median, "x")}.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  ["−2 SD", "minus_2sd"],
                  ["−1 SD", "minus_1sd"],
                  ["Mean", "mean"],
                  ["+1 SD", "plus_1sd"],
                  ["+2 SD", "plus_2sd"],
                ].map(([label, key]) => (
                  <div
                    className="p-3 rounded-lg bg-bg border border-border"
                    key={key}
                  >
                    <p className="text-xs text-mutedText">{label}</p>
                    <p className="font-semibold text-lg">
                      {number(bands[key], "x")}
                    </p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <EmptyState title="Not enough comparable annual observations">
              At least three matching positive annual denominators and
              fiscal-end prices are required. No synthetic history is
              substituted.
            </EmptyState>
          )}
          {data.observations?.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr>
                    <th className="p-2">Fiscal period</th>
                    <th className="p-2">Price date</th>
                    <th className="p-2">P/E</th>
                    <th className="p-2">P/B</th>
                  </tr>
                </thead>
                <tbody>
                  {data.observations.map((o: any) => (
                    <tr key={o.date} className="border-t border-border">
                      <td className="p-2">{o.date}</td>
                      <td className="p-2">{o.price_date}</td>
                      <td className="p-2">{number(o.pe, "x")}</td>
                      <td className="p-2">{number(o.pb, "x")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="text-xs text-mutedText leading-relaxed">
            {data.methodology}
          </p>
        </section>
      )}
    </ResourceState>
  );
}
