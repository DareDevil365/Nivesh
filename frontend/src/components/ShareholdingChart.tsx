"use client";
import { useResource, ResourceState, EmptyState, number } from "@/lib/research";
export function ShareholdingChart({ ticker }: { ticker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/shareholding`,
  );
  const data = resource.data;
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="space-y-3">
          <h3 className="font-semibold">Ownership disclosures</h3>
          <EmptyState title="Exchange shareholding data unavailable">
            {data.message}
          </EmptyState>
          <p className="text-xs text-mutedText">
            Provider insider ownership: {number(data.insider_holding, "%")} ·
            This is a separate classification and is not shown as promoter
            ownership.
          </p>
          <a
            href={data.source_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-primary"
          >
            View official NSE shareholding disclosures ↗
          </a>
        </section>
      )}
    </ResourceState>
  );
}
