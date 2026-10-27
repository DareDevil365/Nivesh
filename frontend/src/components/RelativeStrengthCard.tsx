"use client";
import { useResource, ResourceState, EmptyState, number } from "@/lib/research";
export default function RelativeStrengthCard({
  ticker,
}: {
  ticker: string;
  price?: number;
  dayChangePct?: number | null;
}) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/technicals`,
  );
  const data = resource.data;
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="border border-border rounded-card p-5 space-y-4">
          <h3 className="font-semibold">Trend & relative performance</h3>
          <p className="text-xs text-mutedText">
            Aligned daily closes; as of {data.as_of || "unavailable"}. Relative
            performance is the stock's period return minus Nifty 50's return in
            percentage points.
          </p>
          {data.as_of ? (
            <div className="grid sm:grid-cols-4 gap-3">
              {[
                ["1-year stock return", data.stock_return_pct, "%"],
                ["1-year Nifty 50 return", data.benchmark_return_pct, "%"],
                ["Relative performance", data.relative_return_pp, " pp"],
                ["Distance from 50-day SMA", data.sma50_distance_pct, "%"],
                ["Distance from 200-day SMA", data.sma200_distance_pct, "%"],
                ["RSI (14)", data.rsi14, ""],
              ].map(([label, value, unit]) => (
                <div key={String(label)} className="p-3 bg-bg rounded-lg">
                  <p className="text-xs text-mutedText">{label}</p>
                  <p className="font-semibold mt-2">
                    {number(value as number | null, String(unit))}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Technical history unavailable">
              {data.message}
            </EmptyState>
          )}
          <p className="text-xs text-mutedText">{data.methodology}</p>
        </section>
      )}
    </ResourceState>
  );
}
