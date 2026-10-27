"use client";
import {
  useResource,
  ResourceState,
  EmptyState,
  number,
  money,
} from "@/lib/research";
export default function ReverseDCFCard({ ticker }: { ticker: string }) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/valuation-bands`,
  );
  const model = resource.data?.reverse_dcf;
  return (
    <ResourceState resource={resource}>
      {model && (
        <section className="rounded-card border border-border p-5 space-y-4">
          <h3 className="font-semibold">
            Cash flow growth implied by the price
          </h3>
          {model.implied_growth_pct == null ? (
            <EmptyState title="Reverse DCF unavailable">
              {model.explanation}
            </EmptyState>
          ) : (
            <>
              <p className="text-3xl text-primary font-heading">
                {number(model.implied_growth_pct, "% / year")}
              </p>
              <p className="text-xs text-mutedText">
                Annual FCF per current share: {money(model.fcf_per_share)}.
                Discount: {model.discount_rate_wacc_pct}%. Terminal growth:{" "}
                {model.terminal_growth_pct}%.
              </p>
              <div className="grid sm:grid-cols-3 gap-3">
                {model.scenarios?.map((s: any) => (
                  <div
                    key={s.label}
                    className="p-4 bg-bg border border-border rounded-lg"
                  >
                    <p className="text-xs text-mutedText">{s.label}</p>
                    <p className="text-xl font-semibold">{money(s.value)}</p>
                    <p className="text-xs text-mutedText">
                      {s.growth_pct}% growth · {s.discount_pct}% discount
                    </p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-mutedText">{model.explanation}</p>
            </>
          )}
        </section>
      )}
    </ResourceState>
  );
}
