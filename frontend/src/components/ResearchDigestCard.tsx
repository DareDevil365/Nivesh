"use client";
import { useResource, ResourceState } from "@/lib/research";
import { ResearchCollectionStatus } from "./ResearchWorkflowPanel";
export default function ResearchDigestCard({
  ticker,
  onOpenResearch,
}: {
  ticker: string;
  onOpenResearch?: () => void;
}) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/research-notes`,
  );
  const data = resource.data;
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="space-y-4">
          <h3 className="font-semibold">
            Research checks & official disclosures
          </h3>
          <p className="text-xs text-mutedText">
            Rule-based checks on provider fundamentals. These are fixed
            thresholds, not verified analyst opinions.
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            {data.rule_based_flags.map((f: any, i: number) => (
              <div
                key={i}
                className="rounded-lg border border-border bg-bg p-3"
              >
                <h4 className="text-sm font-semibold">{f.label}</h4>
                <p className="text-xs text-mutedText mt-2">{f.text}</p>
              </div>
            ))}
          </div>
          <ResearchCollectionStatus
            ticker={ticker}
            onOpenResearch={onOpenResearch}
          />
          <div className="flex flex-wrap gap-4 text-xs text-primary">
            <a
              target="_blank"
              rel="noreferrer"
              href={data.official_exchange_filings_url}
            >
              NSE announcements ↗
            </a>
            <a
              target="_blank"
              rel="noreferrer"
              href={data.bse_announcements_url}
            >
              BSE announcements ↗
            </a>
          </div>
        </section>
      )}
    </ResourceState>
  );
}
