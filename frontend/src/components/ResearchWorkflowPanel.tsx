"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import CompanyDevelopmentsPanel from "@/components/CompanyDevelopmentsPanel";
import {
  useResource,
  ResourceState,
  dateTime,
  money,
  number,
  download,
} from "@/lib/research";

const active = (status?: string) =>
  ["queued", "running"].includes(status || "");

export function ResearchCollectionStatus({
  ticker,
  onCompleted,
  onOpenResearch,
}: {
  ticker: string;
  onCompleted?: () => void;
  onOpenResearch?: () => void;
}) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/research-workflow`,
  );
  const data = resource.data;
  useEffect(() => {
    if (!active(data?.status)) return;
    const timer = setTimeout(resource.reload, 3000);
    return () => clearTimeout(timer);
  }, [data, resource.reload]);
  useEffect(() => {
    if (data?.finished_at) onCompleted?.();
  }, [data?.finished_at, onCompleted]);
  return (
    <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-2">
      <p className="text-sm font-semibold">Live company-report research</p>
      <p role="status" className="text-xs text-mutedText">
        {resource.error || data?.progress || "Checking public issuer filings…"}
      </p>
      <p className="text-xs text-mutedText">
        {data?.documents?.length || 0} documents read ·{" "}
        {data?.relationship_count || 0} extracted relationships. Collection uses
        the selected issuer, with no saved company map.
      </p>
      {onOpenResearch && (
        <button onClick={onOpenResearch} className="text-xs text-primary">
          Open sources, evidence and research workflow →
        </button>
      )}
    </div>
  );
}

function ScenarioBuilder({
  inputs,
  filingRecords,
  onModelChange,
}: {
  inputs: any;
  filingRecords: any[];
  onModelChange: (model: any) => void;
}) {
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [selectedFiling, setSelectedFiling] = useState<any>(null);
  const filingGroups = new Map<string, any>();
  for (const row of filingRecords || []) {
    if (row.period_kind !== "annual") continue;
    const key = `${row.id}:${row.basis}:${row.period}`;
    const group = filingGroups.get(key) || {
      key,
      period: row.period,
      basis: row.basis,
      url: row.url,
      page: row.page,
      title: row.title,
    };
    group[row.metric] = row.value_cr;
    filingGroups.set(key, group);
  }
  const filingOptions = Array.from(filingGroups.values())
    .filter((row) => row.revenue_cr != null && row.net_income_cr != null)
    .sort((a, b) => b.period.localeCompare(a.period));
  const [cases, setCases] = useState([
    { label: "Bear", growth: -5, marginChange: -2, multiple: 15 },
    { label: "Base", growth: 5, marginChange: 0, multiple: 20 },
    { label: "Bull", growth: 15, marginChange: 2, multiple: 25 },
  ]);
  const baseline = (key: string) =>
    key in overrides
      ? overrides[key].trim() === ""
        ? null
        : Number(overrides[key])
      : inputs?.[key];
  const revenue = baseline("revenue_cr");
  const profit = baseline("net_income_cr");
  const shares = baseline("shares_outstanding");
  const currentPrice = baseline("current_price");
  useEffect(() => {
    onModelChange({
      cases,
      overrides,
      reported_inputs: inputs,
      selected_filing_baseline: selectedFiling,
      method:
        "One-year revenue × net margin / fixed current shares × assumed P/E; edits and case defaults are user assumptions.",
    });
  }, [cases, overrides, inputs, selectedFiling, onModelChange]);
  const valid =
    Number.isFinite(revenue) &&
    revenue > 0 &&
    Number.isFinite(profit) &&
    Number.isFinite(shares) &&
    shares > 0;
  const financialSector = /financial|bank|insurance/i.test(
    inputs?.sector || "",
  );
  const baseMargin = valid ? (profit / revenue) * 100 : 0;
  return (
    <section className="space-y-3 border border-border rounded-xl p-4">
      <h3 className="font-semibold">Test your operating assumptions</h3>
      <p className="text-xs text-mutedText">
        A one-year learning model: revenue × net margin → net profit → earnings
        per current share → assumed P/E. Inputs below are illustrative user
        assumptions, not AI predictions. Share count is held constant; debt,
        dilution, tax and working capital are not forecast separately.
      </p>
      <p className="text-xs text-mutedText">
        Baseline figures use reported values when available. Edits below are
        your assumptions, not verified company facts. Check the share-capital
        note for missing share counts; do not substitute IPO offer size for
        total shares.
      </p>
      {!!filingOptions.length && (
        <label className="block text-xs text-mutedText">
          Choose a consistent annual filing basis
          <select
            aria-label="Annual filing baseline"
            value={selectedFiling?.key || ""}
            onChange={(event) => {
              const selected = filingOptions.find(
                (item) => item.key === event.target.value,
              );
              setSelectedFiling(selected || null);
              setOverrides((previous) => {
                const updated = { ...previous };
                if (selected) {
                  updated.revenue_cr = String(selected.revenue_cr);
                  updated.net_income_cr = String(selected.net_income_cr);
                } else {
                  delete updated.revenue_cr;
                  delete updated.net_income_cr;
                }
                return updated;
              });
            }}
            className="block w-full mt-2 border border-border rounded bg-bg p-2"
          >
            <option value="">
              Provider baseline · reporting basis unconfirmed
            </option>
            {filingOptions.map((item) => (
              <option key={item.key} value={item.key}>
                {item.period} · {item.basis} · page {item.page} · {item.title}
              </option>
            ))}
          </select>
          <span className="block mt-1">
            Only annual revenue and net income are selected from the same table.
            Current shares and price retain their separately labelled sources.
          </span>
        </label>
      )}
      {selectedFiling && (
        <p className="text-xs text-primary">
          Selected {selectedFiling.basis} income table ·{" "}
          <a
            href={`${selectedFiling.url}#page=${selectedFiling.page}`}
            target="_blank"
            rel="noreferrer"
            className="underline"
          >
            Verify original page {selectedFiling.page} ↗
          </a>
        </p>
      )}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {(
          [
            ["revenue_cr", "Annual revenue (₹ Cr)"],
            ["net_income_cr", "Annual net profit (₹ Cr)"],
            ["shares_outstanding", "Current shares outstanding (units)"],
            ["current_price", "Reference share price (₹)"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="text-xs text-mutedText">
            {label}
            <input
              type="number"
              step="any"
              value={key in overrides ? overrides[key] : (inputs?.[key] ?? "")}
              onChange={(event) => {
                if (key === "revenue_cr" || key === "net_income_cr")
                  setSelectedFiling(null);
                setOverrides((previous) => ({
                  ...previous,
                  [key]: event.target.value,
                }));
              }}
              className="w-full mt-1 border border-border rounded bg-bg p-2 text-neutralText"
            />
            <span className="block mt-1">
              {key in overrides
                ? selectedFiling &&
                  (key === "revenue_cr" || key === "net_income_cr")
                  ? `Selected ${selectedFiling.basis} filing`
                  : "User assumption"
                : inputs?.[key] == null
                  ? "Missing — supply with evidence"
                  : "Provider value"}
            </span>
          </label>
        ))}
      </div>
      {!valid || financialSector ? (
        <p className="text-sm text-mutedText">
          {financialSector
            ? "This generic revenue/margin model is unsuitable for banks and insurers. Use a sector-specific model."
            : "Positive revenue, finite net income and a positive share count are needed. Investigate missing inputs in the filing, then enter your documented assumption above."}
        </p>
      ) : (
        <>
          <p className="text-xs text-mutedText">
            Starting annual period:{" "}
            {selectedFiling?.period || inputs?.period || "Not supplied"} ·
            Revenue {money(revenue)} Cr · Net margin {number(baseMargin, "%")} ·
            Current reference price {money(currentPrice)}
          </p>
          <div className="grid md:grid-cols-3 gap-3">
            {cases.map((scenario, index) => {
              const margin = baseMargin + scenario.marginChange;
              const projectedRevenue = revenue * (1 + scenario.growth / 100);
              const eps = (((projectedRevenue * margin) / 100) * 1e7) / shares;
              const computedPrice = eps * scenario.multiple;
              const price =
                eps > 0 && Number.isFinite(computedPrice)
                  ? computedPrice
                  : null;
              return (
                <div
                  key={scenario.label}
                  className="rounded-lg border border-border bg-bg p-4 space-y-3"
                >
                  <h4 className="font-semibold text-sm">
                    {scenario.label} assumption
                  </h4>
                  {(
                    [
                      ["growth", "Revenue growth (%)", -90, 100],
                      [
                        "marginChange",
                        "Net-margin change (percentage points)",
                        -30,
                        30,
                      ],
                      ["multiple", "Assumed P/E (×)", 1, 100],
                    ] as const
                  ).map(([key, label, min, max]) => (
                    <label key={key} className="block text-xs text-mutedText">
                      {label}
                      <input
                        type="number"
                        step="0.5"
                        min={min}
                        max={max}
                        value={scenario[key]}
                        onChange={(event) => {
                          const value = Number(event.target.value);
                          if (!Number.isFinite(value)) return;
                          setCases((previous) =>
                            previous.map((item, i) =>
                              i === index
                                ? {
                                    ...item,
                                    [key]: Math.max(min, Math.min(max, value)),
                                  }
                                : item,
                            ),
                          );
                        }}
                        className="mt-1 w-full bg-surface border border-border rounded p-2 text-neutralText"
                      />
                    </label>
                  ))}
                  <p className="text-xs text-mutedText">
                    Projected revenue: {money(projectedRevenue)} Cr
                    <br />
                    Projected net margin: {number(margin, "%")}
                    <br />
                    Projected EPS: {money(eps)}
                  </p>
                  <p className="font-semibold text-primary">
                    {price == null
                      ? "P/E valuation unavailable: non-positive earnings or numerical limits exceeded"
                      : `Scenario price: ${money(price)}`}
                  </p>
                  {price != null && currentPrice > 0 && (
                    <p className="text-xs text-mutedText">
                      {number((price / currentPrice - 1) * 100, "%")} price
                      change, excluding dividends
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}

export default function ResearchWorkflowPanel({
  ticker,
  onOpenAi,
}: {
  ticker: string;
  onOpenAi?: () => void;
}) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/research-workflow`,
  );
  const [urls, setUrls] = useState("");
  const [contextUrls, setContextUrls] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [audit, setAudit] = useState<any>(null);
  const [auditing, setAuditing] = useState(false);
  const [scenarioModel, setScenarioModel] = useState<any>(null);
  const [category, setCategory] = useState("supply_chain");
  const [limit, setLimit] = useState(8);
  const [hypothesis, setHypothesis] = useState("");
  const [storageNote, setStorageNote] = useState("");
  const data = resource.data;
  const runAudit = async () => {
    setAuditing(true);
    setError("");
    try {
      setAudit(
        await api.get(
          `/api/companies/${encodeURIComponent(ticker)}/research-audit`,
        ),
      );
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setAuditing(false);
    }
  };
  useEffect(() => {
    setAudit(null);
  }, [ticker, data?.finished_at]);
  useEffect(() => {
    if (!active(data?.status)) return;
    const timer = setTimeout(resource.reload, 3000);
    return () => clearTimeout(timer);
  }, [data, resource.reload]);
  useEffect(() => {
    try {
      setHypothesis(localStorage.getItem(`nivesh-hypothesis:${ticker}`) || "");
    } catch {
      setStorageNote(
        "Browser storage is unavailable. Export your work before leaving.",
      );
    }
  }, [ticker]);
  const run = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const source_urls = urls
        .split(/\n/)
        .map((value) => value.trim())
        .filter(Boolean);
      if (source_urls.length > 3)
        throw new Error("Add at most three source URLs per run.");
      const context_urls = contextUrls
        .split(/\n/)
        .map((value) => value.trim())
        .filter(Boolean);
      if (context_urls.length > 3)
        throw new Error("Add at most three official context URLs per run.");
      await api.post(
        `/api/companies/${encodeURIComponent(ticker)}/research-workflow`,
        { source_urls, context_urls },
      );
      resource.reload();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const allPassages = (data?.documents || []).flatMap(
    (document: any) => document.passages || [],
  );
  const passages = allPassages.filter(
    (passage: any) => passage.category === category,
  );
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="space-y-5">
          <div className="flex flex-wrap justify-between gap-3">
            <div>
              <h2 className="font-semibold text-lg">
                Evidence-backed research workspace
              </h2>
              <p className="text-sm text-mutedText mt-2">
                Collect sources → map the business → test financial quality →
                form hypotheses → build scenarios.
              </p>
            </div>
            <button
              onClick={() =>
                download(
                  `${ticker}-research-evidence.json`,
                  JSON.stringify(
                    {
                      ...data,
                      hypothesis,
                      scenario_model: scenarioModel,
                      exported_at: new Date().toISOString(),
                    },
                    null,
                    2,
                  ),
                  "application/json",
                )
              }
              className="border border-border rounded-lg px-3 py-2 text-xs"
            >
              Export evidence pack
            </button>
          </div>
          <form
            onSubmit={run}
            className="bg-bg rounded-xl border border-border p-4 space-y-3"
          >
            <p role="status" className="text-sm text-primary">
              {data.progress || "Ready to collect sources."}
            </p>
            <p className="text-xs text-mutedText">
              Discovery checks NSE annual reports, IPO documents, recent
              announcements and the company's public investor pages. Collection
              runs in the background and may take several minutes for large
              reports.
            </p>
            <details>
              <summary className="text-xs text-primary cursor-pointer">
                Add an official report that discovery missed
              </summary>
              <label
                htmlFor="research-source-urls"
                className="block text-xs text-mutedText mt-3"
              >
                Public HTTPS PDF or ZIP URLs, one per line; maximum three.
                Company website, NSE, BSE or SEBI sources.
              </label>
              <textarea
                id="research-source-urls"
                rows={3}
                value={urls}
                maxLength={6000}
                onChange={(event) => setUrls(event.target.value)}
                placeholder="https://…/annual-report.pdf"
                className="w-full mt-2 bg-surface rounded border border-border p-3 text-sm"
              />
            </details>
            <details>
              <summary className="text-xs text-primary cursor-pointer">
                Add official policy or industry context
              </summary>
              <label
                htmlFor="research-context-urls"
                className="block text-xs text-mutedText mt-3"
              >
                Public HTML articles from PIB, RBI, MoSPI, Commerce, IMF, World
                Bank or Federal Reserve. One URL per line; maximum three.
                Previously supplied URLs are reused on refresh.
              </label>
              <textarea
                id="research-context-urls"
                rows={3}
                value={contextUrls}
                maxLength={6000}
                onChange={(event) => setContextUrls(event.target.value)}
                placeholder="https://www.pib.gov.in/…"
                className="w-full mt-2 bg-surface rounded border border-border p-3 text-sm"
              />
            </details>
            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={busy || active(data.status)}
                className="rounded-lg bg-primary px-4 py-2 text-xs text-white disabled:opacity-50"
              >
                {active(data.status)
                  ? "Collecting and reading reports…"
                  : "Collect / refresh company evidence"}
              </button>
              {onOpenAi && (
                <button
                  type="button"
                  onClick={onOpenAi}
                  className="rounded-lg border border-border px-4 py-2 text-xs"
                >
                  Interpret collected evidence with AI →
                </button>
              )}
            </div>
            {error && (
              <p role="alert" className="text-sm text-negative">
                {error}
              </p>
            )}
            {data.finished_at && (
              <p className="text-xs text-mutedText">
                Last collection finished {dateTime(data.finished_at)} IST ·{" "}
                {data.documents.length} documents read
              </p>
            )}
          </form>
          <CompanyDevelopmentsPanel
            ticker={ticker}
            collectionVersion={data.finished_at || data.status}
          />
          <section className="border border-border rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-semibold">Evidence coverage</h3>
            <p className="text-xs text-mutedText">
              Passages found by keyword retrieval. A match does not mean the
              topic is answered; no match does not mean the company has no
              exposure.
            </p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-2">
              {data.coverage?.map((item: any) => (
                <p
                  key={item.category}
                  className="text-xs border border-border rounded p-2"
                >
                  {item.category.replaceAll("_", " ")}:{" "}
                  {item.passages
                    ? `${item.passages} passages to review`
                    : "Missing evidence"}
                </p>
              ))}
            </div>
            <button
              type="button"
              disabled={auditing || active(data.status)}
              onClick={runAudit}
              className="border border-border rounded-lg px-3 py-2 text-xs disabled:opacity-50"
            >
              {auditing
                ? "Checking evidence and financial contracts…"
                : "Run data & evidence checks"}
            </button>
            {audit && (
              <details open className="text-xs text-mutedText">
                <summary className="cursor-pointer">
                  Check results: {audit.status.replaceAll("_", " ")} ·{" "}
                  {
                    audit.checks.filter((item: any) => item.status === "fail")
                      .length
                  }{" "}
                  failures
                </summary>
                <p className="mt-2">
                  These checks do not certify AI interpretation or source
                  completeness. Original PDF quote verification is available
                  through the audit script.
                </p>
                <ul className="mt-2 space-y-1 max-h-72 overflow-y-auto">
                  {audit.checks.map((item: any, index: number) => (
                    <li
                      key={index}
                      className={
                        item.status === "fail"
                          ? "text-negative"
                          : item.status === "warning"
                            ? "text-amber-300"
                            : ""
                      }
                    >
                      {item.status.toUpperCase()} · {item.check}: {item.detail}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            {!!data.previous_documents?.length && (
              <details className="text-xs text-mutedText">
                <summary className="cursor-pointer">
                  Previous collection ({data.previous_documents.length}{" "}
                  documents; excluded from current analysis)
                </summary>
                <p className="mt-2">
                  Retained for comparison. These documents were not successfully
                  collected in the current run.
                </p>
                {data.previous_documents.map((doc: any) => (
                  <a
                    key={doc.id}
                    href={doc.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block text-primary mt-1"
                  >
                    {doc.title} ↗
                  </a>
                ))}
              </details>
            )}
          </section>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.documents.map((document: any) => (
              <article
                key={document.id}
                className="border border-border rounded-xl p-4 space-y-2"
              >
                <h3 className="font-semibold text-sm">{document.title}</h3>
                <p className="text-xs text-mutedText">
                  {document.discovered_via} ·{" "}
                  {document.source_kind === "company_page"
                    ? "Company HTML business page"
                    : `${document.pages_read}/${document.total_pages} PDF pages read`}
                  {document.partial ? " · partial coverage" : ""}
                </p>
                <p className="text-xs text-mutedText">
                  Publication date: {document.date || "Not supplied"}.{" "}
                  {document.date_note}
                </p>
                <a
                  href={document.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-primary"
                >
                  Open original document ↗
                </a>
              </article>
            ))}
          </div>
          <section className="border border-border rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-semibold">
              Official policy & news leads
            </h3>
            <p className="text-xs text-mutedText">
              The collector checks current PIB and RBI feeds for company,
              industry and macro keywords. Check eligibility, implementation
              dates, exposure and contrary evidence before assigning a financial
              effect.
            </p>
            {!data.context?.articles?.length && (
              <p className="text-xs text-amber-300">
                No readable contextual sources collected. This does not mean
                there is no relevant policy or news.
              </p>
            )}
            {!!data.context?.candidates?.length && (
              <details className="text-xs text-mutedText">
                <summary className="cursor-pointer">
                  Official feed headlines ({data.context.candidates.length};
                  full article may be unavailable)
                </summary>
                <div className="mt-2 space-y-2">
                  {data.context.candidates.map((item: any) => (
                    <p key={item.url}>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary"
                      >
                        {item.title} ↗
                      </a>
                      <span className="block">
                        Feed date: {item.date || "Not supplied"} · Matched:{" "}
                        {item.matched_terms.join(", ")}. Headline alone does not
                        establish policy details or company impact.
                      </span>
                    </p>
                  ))}
                </div>
              </details>
            )}
            {data.context?.articles?.map((article: any) => (
              <details
                key={article.id}
                className="border border-border rounded-lg p-3 text-xs text-mutedText"
              >
                <summary className="cursor-pointer text-neutralText">
                  {article.title}
                </summary>
                <p className="mt-2">
                  Source-reported date: {article.date || "Not supplied"} ·
                  Company impact unverified
                </p>
                {article.date_warning && (
                  <p className="mt-1 text-amber-300">{article.date_warning}</p>
                )}
                <p className="mt-2">
                  Matched terms:{" "}
                  {article.matched_terms.join(", ") || "User-supplied source"}
                </p>
                <p className="mt-2 whitespace-pre-wrap">
                  {article.text.slice(0, 4000)}
                  {article.text.length > 4000
                    ? " … Open the original for the full text."
                    : ""}
                </p>
                <a
                  className="inline-block mt-2 text-primary"
                  href={article.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open official source ↗
                </a>
              </details>
            ))}
            {[
              ...(data.context?.attempts || []),
              ...(data.context?.errors || []),
            ].map((item: any, index: number) => (
              <p key={index} className="text-xs text-mutedText">
                {item.source || "Context article"}:{" "}
                {item.status || "unavailable"}
                {item.message ? ` — ${item.message}` : ""}
              </p>
            ))}
            {data.context?.limitations && (
              <p className="text-xs text-mutedText">
                {data.context.limitations}
              </p>
            )}
          </section>

          <details className="border border-border rounded-xl p-4">
            <summary className="text-sm cursor-pointer">
              Collection coverage & source failures
            </summary>
            <ul className="text-xs text-mutedText mt-3 space-y-2">
              {data.attempts.map((attempt: any, i: number) => (
                <li key={i}>
                  {attempt.source}: {attempt.status}
                  {attempt.message ? ` — ${attempt.message}` : ""}
                </li>
              ))}
              {data.errors.map((issue: any, i: number) => (
                <li key={`error-${i}`} className="text-amber-300">
                  {issue.message}{" "}
                  {issue.url && (
                    <a
                      href={issue.url}
                      target="_blank"
                      rel="noreferrer"
                      className="underline"
                    >
                      Inspect source ↗
                    </a>
                  )}
                </li>
              ))}
              {data.limitations?.map((note: string) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </details>
          {data.financial_reconciliation && (
            <section className="border border-border rounded-xl p-4 space-y-3">
              <h3 className="font-semibold text-sm">
                Cross-check provider inputs against filings
              </h3>
              <p className="text-xs text-mutedText">
                {data.financial_reconciliation.note}
              </p>
              {!data.financial_reconciliation.records.length && (
                <p className="text-xs text-amber-300">
                  No unambiguous income table parsed. Do not treat this as
                  validation of the provider figures.
                </p>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-mutedText">
                      <th className="p-2">Period / basis</th>
                      <th className="p-2">Metric</th>
                      <th className="p-2">Filing (₹ Cr)</th>
                      <th className="p-2">Provider (₹ Cr)</th>
                      <th className="p-2">Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.financial_reconciliation.comparisons.map(
                      (row: any, index: number) => (
                        <tr key={index} className="border-t border-border">
                          <td className="p-2 whitespace-nowrap">
                            {row.period}
                            <br />
                            {row.basis}
                          </td>
                          <td className="p-2">
                            {row.metric.replaceAll("_", " ")}
                          </td>
                          <td className="p-2">{number(row.value_cr)}</td>
                          <td className="p-2">
                            {number(row.provider_value_cr)}
                            <span className="block text-amber-300">
                              {row.status.replaceAll("_", " ")}
                            </span>
                          </td>
                          <td className="p-2">
                            <a
                              href={`${row.url}#page=${row.page}`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-primary"
                            >
                              Page {row.page} ↗
                            </a>
                            <span className="block text-mutedText">
                              Original unit: {row.reported_unit}
                            </span>
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-mutedText">
                The parser supports explicit, aligned income tables only. Values
                remain separate; select an annual filing basis below before
                using them in a scenario.
              </p>
            </section>
          )}
          {data.research_plan && (
            <section className="space-y-3">
              <h3 className="font-semibold">
                Research questions for this business
              </h3>
              <p className="text-xs text-mutedText">
                {data.research_plan.classification_basis} ·{" "}
                {data.research_plan.business_template.replaceAll("_", " ")}
              </p>
              <div className="grid md:grid-cols-3 gap-3">
                {data.research_plan.checks.map((check: any) => (
                  <details
                    key={check.title}
                    className="border border-border rounded-xl p-4"
                  >
                    <summary className="text-sm font-semibold cursor-pointer">
                      {check.title}
                    </summary>
                    <p className="text-xs text-mutedText mt-3">
                      {check.question}
                    </p>
                    <p className="text-xs text-amber-300 mt-2">
                      {check.status.replaceAll("_", " ")} · Matches are inputs
                      to review, not conclusions.
                    </p>
                    {check.evidence_ids.slice(0, 3).map((id: string) => {
                      const passage = allPassages.find(
                        (item: any) => item.id === id,
                      );
                      return (
                        passage && (
                          <div key={id} className="mt-3 text-xs text-mutedText">
                            <p>{passage.text.slice(0, 220)}…</p>
                            <a
                              className="text-primary"
                              href={
                                passage.page
                                  ? `${passage.url}#page=${passage.page}`
                                  : passage.url
                              }
                              target="_blank"
                              rel="noreferrer"
                            >
                              {passage.title}
                              {passage.page ? ` · page ${passage.page}` : ""} ↗
                            </a>
                          </div>
                        )
                      );
                    })}
                  </details>
                ))}
              </div>
            </section>
          )}
          <section className="space-y-3">
            <h3 className="font-semibold">
              Read the evidence before drawing conclusions
            </h3>
            <div className="flex flex-wrap gap-2">
              {[
                "operations",
                "guidance",
                "concentration",
                "business",
                "supply_chain",
                "competition",
                "demand",
                "risks",
                "governance",
                "financials",
                "policy",
              ].map((key) => (
                <button
                  key={key}
                  aria-pressed={key === category}
                  onClick={() => {
                    setCategory(key);
                    setLimit(8);
                  }}
                  className={`text-xs border rounded-lg px-3 py-2 ${key === category ? "border-primary text-primary" : "border-border text-mutedText"}`}
                >
                  {key.replace("_", " ")}
                </button>
              ))}
            </div>
            {!passages.length && (
              <p className="text-sm text-mutedText">
                No extracted passage in this category yet. Check collection
                status or add a relevant official report.
              </p>
            )}
            <div className="grid md:grid-cols-2 gap-3">
              {passages.slice(0, limit).map((passage: any) => (
                <article
                  key={passage.id}
                  className="border border-border rounded-xl bg-bg p-4 space-y-3"
                >
                  <p className="text-xs text-primary">
                    {passage.title} · PDF page {passage.page}
                  </p>
                  <p className="text-sm text-mutedText leading-relaxed">
                    {passage.text}
                  </p>
                  <a
                    href={
                      passage.url.toLowerCase().includes(".zip")
                        ? passage.url
                        : `${passage.url.split("#")[0]}#page=${passage.page}`
                    }
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-primary"
                  >
                    Verify original page / archive ↗
                  </a>
                </article>
              ))}
            </div>
            {passages.length > limit && (
              <button
                onClick={() => setLimit((value) => value + 8)}
                className="text-xs text-primary"
              >
                Show more evidence ({passages.length - limit} remaining)
              </button>
            )}
          </section>
          <section className="space-y-3">
            <h3 className="font-semibold">
              Work through the analyst's questions
            </h3>
            <p className="text-xs text-mutedText">
              Collected passages are inputs to analysis. These questions are not
              automatically answered just because a report was downloaded.
            </p>
            <div className="grid md:grid-cols-2 gap-3">
              {data.stages.map((stage: any, index: number) => (
                <details
                  key={stage.id}
                  className="rounded-xl border border-border p-4"
                >
                  <summary className="text-sm font-semibold cursor-pointer">
                    {index + 1}. {stage.title}
                  </summary>
                  <p className="text-xs text-primary mt-3">{stage.method}</p>
                  <ul className="text-sm text-mutedText mt-3 space-y-2">
                    {stage.questions.map((question: string) => (
                      <li key={question}>• {question}</li>
                    ))}
                  </ul>
                  <p className="text-xs text-mutedText mt-3">
                    Evidence to seek: {stage.evidence.join("; ")}.
                  </p>
                </details>
              ))}
            </div>
          </section>
          <ScenarioBuilder
            key={ticker}
            inputs={data.financial_inputs}
            filingRecords={data.financial_reconciliation?.records || []}
            onModelChange={setScenarioModel}
          />
          <section className="space-y-3">
            <h3 className="font-semibold">
              Record a testable investment hypothesis
            </h3>
            <p className="text-xs text-mutedText">
              Separate reported facts, your assumptions and contrary evidence.
              Your notes stay in this browser and are included in the
              evidence-pack export.
            </p>
            <textarea
              aria-label="Investment hypothesis"
              rows={9}
              maxLength={50000}
              value={hypothesis}
              onChange={(event) => {
                setHypothesis(event.target.value);
                try {
                  localStorage.setItem(
                    `nivesh-hypothesis:${ticker}`,
                    event.target.value,
                  );
                  setStorageNote("Saved in this browser.");
                } catch {
                  setStorageNote(
                    "Could not save. Export your work before leaving.",
                  );
                }
              }}
              className="w-full bg-bg border border-border rounded-xl p-4 text-sm leading-relaxed"
              placeholder={
                "Claim and time horizon:\nReported facts and source pages:\nDemand / cost / policy assumptions:\nExpected revenue, margin and cash effect:\nContrary evidence:\nWhat would invalidate this view:\nMetric and date to review:"
              }
            />
            <p role="status" className="text-xs text-mutedText">
              {storageNote}
            </p>
          </section>
        </section>
      )}
    </ResourceState>
  );
}
