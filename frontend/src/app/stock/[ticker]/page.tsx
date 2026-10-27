"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  useResource,
  ResourceState,
  number,
  money,
  dateTime,
  download,
} from "@/lib/research";
import SnowflakeChart from "@/components/SnowflakeChart";
import StockChart from "@/components/StockChart";
import { FinancialStatements } from "@/components/FinancialStatements";
import QuarterlyResults from "@/components/QuarterlyResults";
import RatioTrends from "@/components/RatioTrends";
import { PeerComparison } from "@/components/PeerComparison";
import GrowthForecastChart from "@/components/GrowthForecastChart";
import DCFCalculator from "@/components/DCFCalculator";
import ValuationBandsChart from "@/components/ValuationBandsChart";
import ReverseDCFCard from "@/components/ReverseDCFCard";
import ForensicRiskCard from "@/components/ForensicRiskCard";
import { ShareholdingChart } from "@/components/ShareholdingChart";
import ResearchDigestCard from "@/components/ResearchDigestCard";
import SupplyChainGraph from "@/components/SupplyChainGraph";
import RelativeStrengthCard from "@/components/RelativeStrengthCard";
import CompanyIntelligencePanel from "@/components/CompanyIntelligencePanel";
import ResearchWorkflowPanel from "@/components/ResearchWorkflowPanel";
import CompanyNewsPanel from "@/components/CompanyNewsPanel";

const TABS = [
  ["overview", "Overview"],
  ["workflow", "Research workflow"],
  ["news", "Company news"],
  ["community", "Community discussion"],
  ["financials", "Financial statements"],
  ["quarterly", "Quarterly results"],
  ["ratios", "Ratios & growth"],
  ["valuation", "Valuation scenarios"],
  ["risk", "Risk & ownership"],
  ["supply", "Supply chain"],
  ["business", "AI deep dive"],
  ["sources", "Research sources"],
  ["notes", "Research notebook"],
];

function Notebook({ ticker }: { ticker: string }) {
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("");
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    setLoaded(false);
    try {
      setNotes(localStorage.getItem(`nivesh-notes:${ticker}`) || "");
      setStatus("");
    } catch {
      setStatus(
        "Browser storage unavailable. Export your notes before leaving.",
      );
    }
    setLoaded(true);
  }, [ticker]);
  const update = (value: string) => {
    setNotes(value);
    try {
      localStorage.setItem(`nivesh-notes:${ticker}`, value);
      setStatus("Saved in this browser");
    } catch {
      setStatus("Could not save. Export your notes before leaving.");
    }
  };
  return (
    <section className="space-y-4">
      <h2 className="font-semibold text-lg">Your research notebook</h2>
      <p className="text-sm text-mutedText">
        Record your thesis, evidence, risks, catalysts and questions to revisit.
        Notes stay in this browser; export a copy for your records.
      </p>
      <label className="block text-sm" htmlFor="research-notes">
        Notes for {ticker}
      </label>
      <textarea
        id="research-notes"
        value={notes}
        disabled={!loaded}
        maxLength={100000}
        onChange={(e) => update(e.target.value)}
        rows={12}
        className="w-full bg-bg border border-border rounded-lg p-4 text-sm leading-relaxed"
        placeholder="Thesis: …
Evidence and source links: …
Risks and what would change my view: …
Next review date: …"
      />
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-mutedText" role="status">
          {status}
        </span>
        <button
          onClick={() =>
            download(
              `${ticker}-notes.md`,
              `# Research notes: ${ticker}

${notes}`,
            )
          }
          className="text-xs border border-border rounded-lg px-4 py-2"
        >
          Export notes
        </button>
      </div>
    </section>
  );
}

export default function StockDashboardPage() {
  const params = useParams();
  const ticker = String(params?.ticker || "RELIANCE.NS").toUpperCase();
  const resource = useResource(`/api/companies/${encodeURIComponent(ticker)}`);
  const company = resource.data;
  const [tab, setTab] = useState("overview");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    setTab("overview");
    setNotice("");
  }, [ticker]);
  const add = async () => {
    try {
      await api.post("/api/watchlist/item", { ticker });
      setNotice("Saved to your watchlist.");
    } catch (error) {
      setNotice((error as Error).message);
    }
  };
  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setNotice("Research link copied.");
    } catch {
      setNotice("Could not copy. Copy the page URL from your browser.");
    }
  };
  const exportMemo = () => {
    if (!company) return;
    const f = company.fundamentals;
    const lines = [
      `# Research snapshot: ${company.name} (${company.ticker})`,
      `Exported: ${new Date().toISOString()}`,
      `Source: ${company.source_url}`,
      `Quote as of: ${company.quote_as_of || "Not supplied"}`,
      `Fetched: ${company.fetched_at}`,
      `Financial period: ${company.financials_as_of || "Not supplied"}`,
      "",
      "## Fundamentals",
      ...Object.entries(f).map(
        ([key, value]) => `- ${key}: ${value == null ? "Unavailable" : value}`,
      ),
      "",
      "## Checklist methodology",
      company.snowflake_scores.methodology,
      "",
      "## Checks",
      ...Object.entries(company.snowflake_scores.checks).flatMap(
        ([axis, checks]) => [
          `### ${axis}`,
          ...(checks as any[]).map(
            (c) =>
              `- ${c.label}: ${!c.available ? "Unavailable" : c.passed ? "Pass" : "Does not pass"}`,
          ),
        ],
      ),
      "",
      "## Limitations",
      company.data_note,
      "",
      "## Notes (your own research)",
    ];
    try {
      lines.push(
        localStorage.getItem(`nivesh-notes:${company.ticker}`) ||
          "No notes saved.",
      );
    } catch {
      lines.push("Browser notes unavailable.");
    }
    download(`${ticker}-research.md`, lines.join("\n"), "text/markdown");
  };
  return (
    <ResourceState resource={resource}>
      {company && (
        <div className="space-y-5">
          <Link
            href="/screener"
            className="text-xs text-mutedText hover:text-primary"
          >
            ← Back to screener
          </Link>
          <section className="rounded-card border border-border bg-surface p-5 md:p-7 space-y-5">
            <div className="flex flex-col md:flex-row justify-between gap-5">
              <div className="space-y-2">
                <p className="text-xs text-primary uppercase tracking-wider">
                  {company.ticker.endsWith(".BO") ? "BSE" : "NSE"} ·{" "}
                  {company.ticker} · {company.instrument_type}
                </p>
                <h1 className="text-2xl md:text-3xl font-heading font-bold">
                  {company.name}
                </h1>
                <p className="text-sm text-mutedText">
                  {company.sector} / {company.industry}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-heading font-bold">
                  {money(company.current_price)}
                </p>
                <p
                  className={`text-sm ${company.day_change_pct == null ? "text-mutedText" : company.day_change_pct >= 0 ? "text-positive" : "text-negative"}`}
                >
                  {number(company.day_change, " ₹")} ·{" "}
                  {number(company.day_change_pct, "%")} vs previous close
                </p>
                <p className="text-xs text-mutedText">
                  Market cap:{" "}
                  {company.market_cap_cr == null
                    ? "—"
                    : `${money(company.market_cap_cr)} Cr`}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={add}
                className="rounded-lg bg-primary text-white px-4 py-2 text-xs font-semibold"
              >
                Add to watchlist
              </button>
              <button
                onClick={exportMemo}
                className="rounded-lg border border-border px-4 py-2 text-xs"
              >
                Export research
              </button>
              <button
                onClick={share}
                className="rounded-lg border border-border px-4 py-2 text-xs"
              >
                Copy link
              </button>
              <button
                onClick={resource.reload}
                className="rounded-lg border border-border px-4 py-2 text-xs"
              >
                Reload data
              </button>
              <a
                href={company.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs px-4 py-2 text-primary"
              >
                Provider source ↗
              </a>
            </div>
            {notice && (
              <p role="status" className="text-sm text-primary">
                {notice}
              </p>
            )}
            <div className="rounded-lg border border-border bg-bg p-3 text-xs text-mutedText space-y-1">
              <p>
                Quote as of:{" "}
                <span className="text-neutralText">
                  {dateTime(company.quote_as_of)}
                  {company.quote_as_of ? " IST" : ""}
                </span>{" "}
                · Fetched: {dateTime(company.fetched_at)} IST · Financial
                period: {company.financials_as_of || "Unavailable"}
              </p>
              <p>{company.data_note} Quotes are cached for up to 15 minutes.</p>
            </div>
            {company.corporate_action_note && (
              <div className="rounded-lg border border-amber-300/30 bg-amber-300/5 p-3 text-xs text-amber-300">
                {company.corporate_action_note}{" "}
                <a
                  target="_blank"
                  rel="noreferrer"
                  href={company.corporate_action_source}
                  className="underline"
                >
                  Exchange notice ↗
                </a>
              </div>
            )}
            {company.symbol_note && (
              <p className="text-xs text-mutedText">{company.symbol_note}</p>
            )}
            {company.about && (
              <details className="text-sm text-mutedText">
                <summary className="cursor-pointer text-neutralText">
                  About the business
                </summary>
                <p className="mt-3 leading-relaxed whitespace-pre-wrap">
                  {company.about}
                </p>
              </details>
            )}
          </section>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            {[
              ["Trailing P/E", company.pe, "x"],
              ["P/B", company.pb, "x"],
              ["EPS (₹)", company.eps, ""],
              ["ROE", company.roe, "%"],
              ["ROCE", company.roce, "%"],
              ["Debt/equity", company.debt_equity, "x"],
              ["Dividend yield", company.div_yield, "%"],
              ["Current ratio", company.current_ratio, "x"],
              ["Revenue CAGR · 3 yr", company.revenue_growth_3yr, "%"],
              ["EPS CAGR · 3 yr", company.eps_growth_3yr, "%"],
              ["52-week high (₹)", company.week_high_52, ""],
              ["52-week low (₹)", company.week_low_52, ""],
            ].map(([label, value, unit]) => (
              <div
                key={String(label)}
                className="rounded-lg border border-border bg-surface p-3"
              >
                <p className="text-[11px] text-mutedText">{label}</p>
                <p className="font-semibold mt-1">
                  {number(value as number | null, String(unit))}
                </p>
              </div>
            ))}
          </div>
          <div className="grid lg:grid-cols-3 gap-5">
            <section className="rounded-card border border-border bg-surface p-4 min-w-0">
              <h2 className="font-semibold">Fundamental checklist</h2>
              <SnowflakeChart scores={company.snowflake_scores} />
              <p className="text-xs text-mutedText">
                Historical growth and fixed thresholds. Missing checks do not
                pass; this is not an analyst forecast.
              </p>
            </section>
            <section className="lg:col-span-2 rounded-card border border-border bg-surface p-4 min-w-0">
              <h2 className="font-semibold mb-4">Price history</h2>
              <StockChart ticker={company.ticker} />
            </section>
          </div>
          <section className="rounded-card border border-border bg-surface overflow-hidden">
            <div
              role="tablist"
              aria-label="Research sections"
              className="flex overflow-x-auto border-b border-border"
            >
              {TABS.map(([id, label]) => (
                <button
                  key={id}
                  id={`tab-${id}`}
                  role="tab"
                  aria-selected={tab === id}
                  aria-controls="research-panel"
                  onClick={() => setTab(id)}
                  className={`whitespace-nowrap px-4 py-4 text-xs border-b-2 ${tab === id ? "border-primary text-primary bg-primary/5" : "border-transparent text-mutedText"}`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div
              id="research-panel"
              role="tabpanel"
              aria-labelledby={`tab-${tab}`}
              className="p-4 md:p-6 space-y-5"
            >
              {tab === "overview" && (
                <>
                  <RelativeStrengthCard
                    ticker={company.ticker}
                    price={company.current_price}
                    dayChangePct={company.day_change_pct}
                  />
                  <div className="grid md:grid-cols-2 gap-4">
                    {[
                      ["Threshold strengths", company.pros],
                      ["Caution flags", company.cons],
                    ].map(([title, items]) => (
                      <div
                        className="bg-bg border border-border rounded-lg p-4"
                        key={String(title)}
                      >
                        <h3 className="font-semibold mb-3">{String(title)}</h3>
                        <ul className="space-y-2 text-sm text-mutedText">
                          {(items as any[]).length ? (
                            (items as any[]).map((item, i) => (
                              <li key={i}>{item.text}</li>
                            ))
                          ) : (
                            <li>No flags computed from available data.</li>
                          )}
                        </ul>
                      </div>
                    ))}
                  </div>
                  <details className="border border-border rounded-lg p-4">
                    <summary className="cursor-pointer text-sm text-primary">
                      How the checklist is calculated
                    </summary>
                    <p className="text-xs text-mutedText mt-3">
                      {company.snowflake_scores.methodology}
                    </p>
                    <div className="grid sm:grid-cols-2 gap-4 mt-4">
                      {Object.entries(company.snowflake_scores.checks).map(
                        ([axis, checks]) => (
                          <div key={axis}>
                            <h3 className="capitalize font-semibold mb-2">
                              {axis} ·{" "}
                              {company.snowflake_scores.available_checks[axis]}
                              /6 inputs available
                            </h3>
                            <ul className="space-y-1 text-xs text-mutedText">
                              {(checks as any[]).map((c) => (
                                <li key={c.label}>
                                  {!c.available ? "?" : c.passed ? "✓" : "·"}{" "}
                                  {c.label}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ),
                      )}
                    </div>
                  </details>
                  <PeerComparison currentTicker={company.ticker} />
                </>
              )}
              {tab === "financials" && (
                <FinancialStatements ticker={company.ticker} />
              )}
              {tab === "quarterly" && (
                <QuarterlyResults ticker={company.ticker} />
              )}
              {tab === "ratios" && (
                <>
                  <RatioTrends ticker={company.ticker} />
                  <GrowthForecastChart ticker={company.ticker} />
                </>
              )}
              {tab === "valuation" && (
                <>
                  <DCFCalculator
                    ticker={company.ticker}
                    currentPrice={company.current_price}
                    fcfPerShare={company.fcf_per_share}
                  />
                  <ReverseDCFCard ticker={company.ticker} />
                  <ValuationBandsChart ticker={company.ticker} />
                </>
              )}
              {tab === "risk" && (
                <>
                  <ForensicRiskCard ticker={company.ticker} />
                  <ShareholdingChart ticker={company.ticker} />
                </>
              )}
              {tab === "business" && (
                <CompanyIntelligencePanel ticker={company.ticker} />
              )}
              {tab === "news" && (
                <CompanyNewsPanel
                  key={`${company.ticker}:news`}
                  ticker={company.ticker}
                />
              )}
              {tab === "community" && (
                <CompanyNewsPanel
                  key={`${company.ticker}:community`}
                  ticker={company.ticker}
                  community
                />
              )}
              {tab === "workflow" && (
                <ResearchWorkflowPanel
                  ticker={company.ticker}
                  onOpenAi={() => setTab("business")}
                />
              )}
              {tab === "supply" && (
                <SupplyChainGraph
                  ticker={company.ticker}
                  onOpenResearch={() => setTab("workflow")}
                />
              )}
              {tab === "sources" && (
                <ResearchDigestCard
                  ticker={company.ticker}
                  onOpenResearch={() => setTab("workflow")}
                />
              )}
              {tab === "notes" && (
                <Notebook key={company.ticker} ticker={company.ticker} />
              )}
            </div>
          </section>
        </div>
      )}
    </ResourceState>
  );
}
