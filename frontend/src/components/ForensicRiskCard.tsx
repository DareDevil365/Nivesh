"use client";
import { useResource, ResourceState, number } from "@/lib/research";
export default function ForensicRiskCard({ ticker }: { ticker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/forensic`,
  );
  const data = resource.data;
  return (
    <ResourceState resource={resource}>
      {data && (
        <div className="space-y-5">
          <div className="text-xs text-mutedText">
            Annual statement period: {data.period || "Unavailable"}.{" "}
            {data.source}
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {[data.altman_z, data.beneish_m].map((model: any) => (
              <div
                key={model.model}
                className="rounded-card border border-border bg-bg p-5 space-y-3"
              >
                <h3 className="font-semibold">{model.model}</h3>
                <p className="text-3xl font-heading">
                  {number(model.score, "", 3)}
                </p>
                <p className="text-sm text-mutedText">
                  {model.zone ||
                    (model.flagged === true
                      ? "Screening threshold exceeded"
                      : model.score == null
                        ? "Unavailable"
                        : "Below screening threshold")}
                </p>
                <p className="text-xs text-mutedText leading-relaxed">
                  {model.description}
                </p>
                {model.missing_inputs?.length > 0 && (
                  <p className="text-xs text-amber-300">
                    Missing or unsupported: {model.missing_inputs.join(", ")}
                  </p>
                )}
                {model.inputs && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-primary">
                      Show calculation inputs
                    </summary>
                    <dl className="mt-2 space-y-1">
                      {Object.entries(model.inputs).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <dt>{k}</dt>
                          <dd>{number(v as number, "", 4)}</dd>
                        </div>
                      ))}
                    </dl>
                  </details>
                )}
              </div>
            ))}
          </div>
          <div className="rounded-card border border-border p-5 space-y-3">
            <h3 className="font-semibold">Cash conversion cycle</h3>
            <p className="text-2xl">
              {number(data.cash_conversion_cycle.ccc_days, " days")}
            </p>
            <p className="text-xs text-mutedText">
              {data.cash_conversion_cycle.description}
            </p>
            <div className="flex flex-wrap gap-5 text-xs">
              {["dio_days", "dso_days", "dpo_days"].map((k) => (
                <span key={k}>
                  {k.split("_")[0].toUpperCase()}:{" "}
                  {number(data.cash_conversion_cycle[k], " days")}
                </span>
              ))}
            </div>
          </div>
          <div className="text-sm text-mutedText">
            {data.promoter_pledge.label}. {data.promoter_pledge.description}
          </div>
        </div>
      )}
    </ResourceState>
  );
}
