"use client";
import { useState } from "react";
import Link from "next/link";
import { ResearchCollectionStatus } from "./ResearchWorkflowPanel";
import { ArrowDown, ArrowRight, Network, ExternalLink } from "lucide-react";
import {
  useResource,
  ResourceState,
  EmptyState,
  number,
  download,
  csvCell,
} from "@/lib/research";

type Node = {
  id: string;
  name: string;
  ticker?: string;
  category: string;
  relationship: string;
  evidence_status: string;
  source_url?: string;
  source_date?: string;
  source_title?: string;
  note?: string;
  source_page?: number;
  evidence_quote?: string;
};
type Mode = "reported" | "leads" | "context";
const directions = [
  "upstream_suppliers",
  "downstream_customers",
  "partners",
] as const;
const count = (network: any) =>
  directions.reduce((n, key) => n + (network?.[key]?.length || 0), 0);

export default function SupplyChainGraph({
  ticker,
  onOpenResearch,
}: {
  ticker: string;
  onOpenResearch?: () => void;
}) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/supply-chain`,
  );
  const [mode, setMode] = useState<Mode | null>(null);
  const [selected, setSelected] = useState<Node | null>(null);
  const [query, setQuery] = useState("");
  const data = resource.data;
  const active = mode || (count(data) ? "reported" : "context");
  const network =
    active === "reported"
      ? data
      : active === "leads"
        ? data?.research_leads
        : data?.sector_context;
  const nodes = (direction: (typeof directions)[number]): Node[] =>
    (network?.[direction] || []).filter((node: Node) =>
      `${node.name} ${node.category} ${node.relationship}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    );
  const exportNetwork = () => {
    const rows = directions.flatMap((direction) =>
      nodes(direction).map((node) => [
        ticker,
        direction,
        node.name,
        node.ticker || "",
        node.relationship,
        node.evidence_status,
        node.source_date || "",
        node.source_url || "",
        node.source_page || "",
        node.evidence_quote || "",
        node.note || "",
      ]),
    );
    download(
      `${ticker}-supply-chain-${active}.csv`,
      [
        [
          "Company",
          "Direction",
          "Counterparty or role",
          "Ticker",
          "Relationship",
          "Evidence",
          "Disclosure date",
          "Source",
          "PDF page",
          "Evidence quote",
          "Limitations",
        ],
        ...rows,
      ]
        .map((row) => row.map(csvCell).join(","))
        .join("\n"),
      "text/csv",
    );
  };
  const nodeCard = (node: Node) => (
    <button
      key={node.id}
      onClick={() => setSelected(node)}
      aria-pressed={selected?.id === node.id}
      className={`w-full text-left rounded-xl border p-4 transition-colors hover:border-primary/60 ${selected?.id === node.id ? "border-primary bg-primary/10" : "border-border bg-bg"}`}
    >
      <span
        className={`text-[10px] uppercase tracking-wide ${active === "leads" ? "text-amber-300" : active === "reported" ? "text-primary" : "text-mutedText"}`}
      >
        {active === "reported"
          ? node.evidence_status === "ai_extracted"
            ? "AI interpretation · cited text"
            : "Extracted disclosure"
          : active === "leads"
            ? "Unverified research lead"
            : "Illustrative role"}
      </span>
      <span className="block text-sm font-semibold mt-2">{node.name}</span>
      <span className="block text-xs text-mutedText mt-1">{node.category}</span>
      <span className="block text-xs text-neutralText mt-2">
        {node.relationship}
      </span>
      {node.source_date && (
        <span className="block text-[11px] text-mutedText mt-2">
          Disclosed {node.source_date}
        </span>
      )}
      <span className="block text-[11px] text-primary mt-2">
        View details →
      </span>
    </button>
  );
  const column = (direction: (typeof directions)[number], title: string) => (
    <div className="min-w-0 space-y-3">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-mutedText">
        {title} ({nodes(direction).length})
      </h4>
      <div className="max-h-[34rem] overflow-y-auto space-y-3 pr-1">
        {nodes(direction).length ? (
          nodes(direction).map(nodeCard)
        ) : (
          <div className="border border-dashed border-border rounded-xl p-4 text-xs text-mutedText">
            {query
              ? "No matching relationships."
              : "No relationships recorded in this direction yet."}
          </div>
        )}
      </div>
    </div>
  );
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="space-y-5">
          <div className="flex flex-wrap justify-between items-start gap-3">
            <div>
              <h2 className="font-semibold text-lg flex gap-2 items-center">
                <Network size={20} className="text-primary" />
                {data.view_type === "etf_holdings"
                  ? "Fund holdings"
                  : "Supply chain & business ecosystem"}
              </h2>
              <p className="text-sm text-mutedText mt-2">
                {data.view_type === "etf_holdings"
                  ? "Explore the fund's provider-reported portfolio."
                  : "Explore inputs, customers and partners. Select a node to inspect its evidence."}
              </p>
            </div>
            {data.view_type !== "etf_holdings" && (
              <button
                onClick={exportNetwork}
                className="text-xs border border-border rounded-lg px-3 py-2"
              >
                Export this view
              </button>
            )}
          </div>
          {data.view_type === "etf_holdings" ? (
            data.holdings?.length ? (
              <div className="grid sm:grid-cols-2 gap-3">
                {data.holdings.map((h: any) => (
                  <div
                    key={h.ticker}
                    className="rounded-lg border border-border p-3"
                  >
                    <div className="flex justify-between gap-3 text-sm">
                      <span>{h.name}</span>
                      <span>{number(h.weight_pct, "%")}</span>
                    </div>
                    <div className="h-1.5 rounded bg-bg mt-2">
                      <div
                        className="h-1.5 bg-primary rounded"
                        style={{ width: `${Math.min(100, h.weight_pct)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="Fund holdings unavailable">
                {data.message}
              </EmptyState>
            )
          ) : (
            <>
              <ResearchCollectionStatus
                ticker={ticker}
                onCompleted={resource.reload}
                onOpenResearch={onOpenResearch}
              />
              <div
                className="flex flex-wrap gap-2"
                role="group"
                aria-label="Supply chain evidence views"
              >
                {(
                  [
                    ["reported", `Sourced relationships (${count(data)})`],
                    ["leads", `Research leads (${count(data.research_leads)})`],
                    ["context", "Sector value chain"],
                  ] as [Mode, string][]
                )
                  .filter(
                    ([key]) =>
                      key !== "leads" || count(data.research_leads) > 0,
                  )
                  .map(([key, label]) => (
                    <button
                      key={key}
                      aria-pressed={active === key}
                      onClick={() => {
                        setMode(key);
                        setSelected(null);
                        setQuery("");
                      }}
                      className={`text-xs rounded-lg px-3 py-2 border ${active === key ? "border-primary text-primary bg-primary/10" : "border-border text-mutedText"}`}
                    >
                      {label}
                    </button>
                  ))}
              </div>
              <p
                className={`text-xs rounded-lg p-3 border ${active === "leads" ? "border-amber-300/30 text-amber-300 bg-amber-300/5" : "border-border text-mutedText bg-bg"}`}
              >
                {active === "reported"
                  ? "Company disclosures with source links and dates. Historical announcements do not establish current contract status, completeness or financial materiality."
                  : active === "leads"
                    ? "Original project mappings restored as research leads. These links and any figures are unverified; confirm them in filings before using them in a thesis."
                    : "An illustrative industry value chain. These roles are research prompts, not claims about this company's actual suppliers or customers."}
              </p>
              <input
                aria-label="Filter supply chain nodes"
                placeholder="Find a company, input or relationship…"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelected(null);
                }}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm"
              />
              <div className="grid md:grid-cols-[1fr_32px_1fr_32px_1fr] items-center gap-4">
                {column("upstream_suppliers", "Upstream · inputs & suppliers")}
                <ArrowRight
                  className="hidden md:block text-primary"
                  aria-hidden="true"
                />
                <ArrowDown
                  className="mx-auto md:hidden text-primary"
                  aria-hidden="true"
                />
                <div className="rounded-2xl border-2 border-primary/60 bg-primary/10 p-6 text-center min-w-0">
                  <Network className="mx-auto text-primary mb-3" size={30} />
                  <h3 className="font-semibold break-words">{data.name}</h3>
                  <p className="text-xs text-primary mt-2">{data.ticker}</p>
                  <p className="text-xs text-mutedText mt-2">{data.sector}</p>
                  <p className="text-[11px] text-mutedText mt-4">
                    Inputs → business → end markets
                  </p>
                </div>
                <ArrowRight
                  className="hidden md:block text-primary"
                  aria-hidden="true"
                />
                <ArrowDown
                  className="mx-auto md:hidden text-primary"
                  aria-hidden="true"
                />
                {column(
                  "downstream_customers",
                  "Downstream · customers & channels",
                )}
              </div>
              {!!nodes("partners").length && (
                <div className="border-t border-border pt-5 space-y-3">
                  <h4 className="text-xs uppercase tracking-wide text-mutedText">
                    Technology, commercial & research partners ↔
                  </h4>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {nodes("partners").map(nodeCard)}
                  </div>
                </div>
              )}
              {selected && (
                <aside
                  aria-label="Relationship details"
                  className="rounded-xl border border-primary/40 bg-primary/5 p-5 space-y-3"
                >
                  <div className="flex justify-between gap-3">
                    <h3 className="font-semibold">{selected.name}</h3>
                    <button
                      onClick={() => setSelected(null)}
                      className="text-xs text-mutedText"
                    >
                      Close details
                    </button>
                  </div>
                  <p className="text-sm">{selected.relationship}</p>
                  <p className="text-xs text-mutedText">{selected.note}</p>
                  {selected.evidence_quote && (
                    <blockquote className="border-l-2 border-primary/50 pl-3 text-sm text-mutedText">
                      “{selected.evidence_quote}”
                    </blockquote>
                  )}
                  {selected.source_page && (
                    <p className="text-xs text-primary">
                      PDF page {selected.source_page}
                    </p>
                  )}
                  <p className="text-xs text-mutedText">
                    Source date: {selected.source_date || "Not recorded"} ·
                    Evidence: {selected.evidence_status.replace("_", " ")}
                  </p>
                  <div className="flex flex-wrap gap-4">
                    {selected.source_url && (
                      <a
                        href={
                          selected.source_page &&
                          !selected.source_url.toLowerCase().includes(".zip")
                            ? `${selected.source_url.split("#")[0]}#page=${selected.source_page}`
                            : selected.source_url
                        }
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-primary inline-flex items-center gap-1"
                      >
                        {selected.source_title || "Open disclosure"}{" "}
                        <ExternalLink size={12} />
                      </a>
                    )}
                    {selected.ticker && (
                      <Link
                        href={`/stock/${encodeURIComponent(selected.ticker)}`}
                        className="text-xs text-primary"
                      >
                        Research {selected.ticker} →
                      </Link>
                    )}
                  </div>
                </aside>
              )}
              {active === "context" && (
                <p className="text-xs text-mutedText">
                  Research next: {data.sector_context?.research_question}
                </p>
              )}
            </>
          )}
          <p className="text-xs text-mutedText">{data.message}</p>
          <a
            href={data.source_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-primary"
          >
            Company / fund provider page ↗
          </a>
        </section>
      )}
    </ResourceState>
  );
}
