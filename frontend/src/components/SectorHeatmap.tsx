"use client";
import { useEffect } from "react";
import Link from "next/link";
import {
  useResource,
  ResourceState,
  EmptyState,
  CoverageNote,
  number,
} from "@/lib/research";
export default function SectorHeatmap() {
  const resource = useResource("/api/screener/sector-heatmap");
  const data = resource.data;
  useEffect(() => {
    if (!data?.coverage?.refreshing) return;
    const timer = setTimeout(resource.reload, 8000);
    return () => clearTimeout(timer);
  }, [data, resource.reload]);
  return (
    <ResourceState resource={resource}>
      {data && (
        <div className="space-y-3">
          <CoverageNote coverage={data.coverage} />
          {data.heatmap.length ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {data.heatmap.map((s: any) => (
                <Link
                  href={`/screener?sector=${encodeURIComponent(s.sector)}`}
                  key={s.sector}
                  className={`rounded-card border p-4 space-y-2 ${s.avg_change_pct >= 0 ? "bg-positive/10 border-positive/20" : "bg-negative/10 border-negative/20"}`}
                >
                  <h3 className="font-semibold text-sm">{s.sector}</h3>
                  <p
                    className={`text-2xl font-heading ${s.avg_change_pct >= 0 ? "text-positive" : "text-negative"}`}
                  >
                    {number(s.avg_change_pct, "%")}
                  </p>
                  <p className="text-xs text-mutedText">
                    {s.stock_count} covered stocks · market-cap weighted
                  </p>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title={
                data.coverage?.refreshing
                  ? "Building the market snapshot…"
                  : "Sector performance unavailable"
              }
            >
              No sample market moves are shown. Refresh the snapshot from the
              screener or retry when the provider is available.
            </EmptyState>
          )}
          <p className="text-xs text-mutedText">
            Moves use each covered stock's latest quote versus its previous
            close. This is a sample of companies, not official NSE sector-index
            performance.
          </p>
        </div>
      )}
    </ResourceState>
  );
}
