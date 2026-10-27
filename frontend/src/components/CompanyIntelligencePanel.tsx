"use client";
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import {
  useResource,
  ResourceState,
  EmptyState,
  dateTime,
  download,
} from "@/lib/research";

export default function CompanyIntelligencePanel({
  ticker,
}: {
  ticker: string;
}) {
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/intelligence`,
  );
  const [generated, setGenerated] = useState<any>(null);
  const [excerpt, setExcerpt] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    setGenerated(null);
    setExcerpt("");
    setSourceUrl("");
    setError("");
  }, [ticker]);
  const data = resource.data;
  const report = generated || data?.deep_dive;
  const generate = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.post(
        `/api/companies/${encodeURIComponent(ticker)}/intelligence`,
        {
          excerpt,
          ...(excerpt.trim() ? { source_url: sourceUrl } : {}),
        },
      );
      setGenerated(result);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const exportReport = () => {
    if (!report) return;
    const sources = new Map<string, any>(
      report.sources.map((source: any) => [source.id, source]),
    );
    const lines = [
      `# AI business deep dive: ${ticker}`,
      `Generated: ${report.generated_at}`,
      `Model: ${report.model}`,
      "",
      report.limitations,
      ...(report.validation_warnings || []).map((warning: string) => `Validation: ${warning}`),
      "",
      ...report.sections.flatMap((section: any) => [
        `## ${section.title}`,
        section.analysis,
        ...(section.interpretation
          ? [`AI hypothesis (unverified): ${section.interpretation}`]
          : []),
        "",
        ...section.evidence.map(
          (evidence: any) =>
            `Evidence: "${evidence.quote}" — ${sources.get(evidence.source_id)?.url || "Unavailable"}`,
        ),
        ...section.questions.map(
          (question: string) => `- To investigate: ${question}`,
        ),
        "",
      ]),
    ];
    download(`${ticker}-ai-deep-dive.md`, lines.join("\n"), "text/markdown");
  };
  return (
    <ResourceState resource={resource}>
      {data && (
        <section className="space-y-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-lg flex gap-2 items-center">
                <Sparkles size={20} className="text-primary" />
                AI business deep dive
              </h2>
              <p className="text-sm text-mutedText mt-2">
                Twelve research lenses, with evidence and questions to
                investigate.
              </p>
            </div>
            {report && (
              <button
                onClick={exportReport}
                className="text-xs border border-border rounded-lg px-3 py-2"
              >
                Export deep dive
              </button>
            )}
          </div>
          <details
            className="rounded-xl border border-border p-4"
            open={!report}
          >
            <summary className="text-sm font-semibold cursor-pointer">
              Provider business description
            </summary>
            {data.what_it_does ? (
              <p className="text-sm text-mutedText leading-relaxed whitespace-pre-wrap mt-3">
                {data.what_it_does}
              </p>
            ) : (
              <EmptyState title="Business description unavailable" />
            )}
            <a
              href={data.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-block text-xs text-primary mt-3"
            >
              Read provider source ↗
            </a>
            <p className="text-xs text-mutedText mt-2">
              Fetched {dateTime(data.fetched_at)} IST
            </p>
          </details>
          <form
            onSubmit={generate}
            className="rounded-xl bg-bg border border-border p-4 space-y-4"
          >
            <details>
              <summary className="cursor-pointer text-sm text-primary">
                Add filing evidence for a deeper analysis (optional)
              </summary>
              <div className="mt-4 space-y-3">
                <label
                  className="block text-xs text-mutedText"
                  htmlFor="filing-excerpt"
                >
                  Annual report or filing excerpt
                </label>
                <textarea
                  id="filing-excerpt"
                  value={excerpt}
                  onChange={(e) => setExcerpt(e.target.value)}
                  rows={5}
                  maxLength={20000}
                  className="w-full rounded-lg border border-border bg-surface p-3 text-sm"
                  placeholder="Paste relevant sections on segments, customers, operations, risks or strategy…"
                />
                <label
                  className="block text-xs text-mutedText"
                  htmlFor="filing-source"
                >
                  Original source URL {excerpt.trim() ? "(required)" : ""}
                </label>
                <input
                  id="filing-source"
                  type="url"
                  required={!!excerpt.trim()}
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  className="w-full rounded-lg border border-border bg-surface p-3 text-sm"
                  placeholder="https://company.example/annual-report.pdf"
                />
              </div>
            </details>
            <p className="text-xs text-mutedText">
              {data.message} Generating sends the description and any pasted
              excerpt to Gemini. Pasted excerpts and their reports are not saved
              on the server.
            </p>
            <p className="text-xs text-primary">
              {data.filings_available || 0} collected company reports available
              to AI. Use Research workflow to collect or refresh reports before
              generating.
            </p>
            {!data.ai_available && (
              <p className="text-xs text-amber-300">
                AI is not configured on this server. Set GEMINI_API_KEY in
                backend/.env and restart the backend to enable generation. Never
                enter an API key in the excerpt.
              </p>
            )}
            <button
              type="submit"
              disabled={busy || !data.ai_available}
              className="rounded-lg bg-primary text-white px-4 py-2 text-xs font-semibold disabled:opacity-50"
            >
              {busy
                ? "Reading evidence and preparing twelve sections…"
                : report
                  ? "Generate another deep dive"
                  : "Generate deep dive"}
            </button>
            {busy && (
              <p role="status" className="text-xs text-mutedText">
                This can take up to a minute. Unsupported topics will become
                research questions.
              </p>
            )}
            {error && (
              <p role="alert" className="text-sm text-negative">
                {error}
              </p>
            )}
          </form>
          {report ? (
            <>
              <p className="text-xs text-mutedText">
                AI interpretation · {report.model} · Generated{" "}
                {dateTime(report.generated_at)} IST
              </p>
              <p className="rounded-lg border border-amber-300/25 p-3 text-xs text-amber-300">
                {report.limitations}
              </p>
              {report.validation_warnings?.length > 0 && (
                <div className="rounded-xl border border-amber-300/40 bg-amber-300/10 p-4 text-sm text-amber-200" role="status">
                  <p className="font-semibold">Partial AI report: some output failed validation</p>
                  <ul className="mt-2 list-disc pl-5 space-y-1">
                    {report.validation_warnings.map((warning: string, index: number) => <li key={index}>{warning}</li>)}
                  </ul>
                  <p className="mt-2">Only accepted evidence is shown. Missing sections need original-source review; generating again may produce different results.</p>
                </div>
              )}
              <div className="grid md:grid-cols-2 gap-4">
                {report.sections.map((section: any) => (
                  <article
                    key={section.id}
                    className="rounded-xl border border-border p-5 space-y-3"
                  >
                    <h3 className="font-semibold text-sm">{section.title}</h3>
                    <p className="text-xs text-primary">
                      {section.evidence.length
                        ? "Quoted source evidence"
                        : "Evidence gap"}
                    </p>
                    <p className="text-sm text-mutedText leading-relaxed whitespace-pre-wrap">
                      {section.analysis}
                    </p>
                    {section.interpretation && (
                      <div className="border border-amber-300/25 rounded-lg p-3 space-y-1">
                        <p className="text-xs text-amber-300">
                          AI hypothesis · interpretation needs review
                        </p>
                        <p className="text-sm text-mutedText whitespace-pre-wrap">
                          {section.interpretation}
                        </p>
                      </div>
                    )}
                    {section.evidence.length ? (
                      <details>
                        <summary className="cursor-pointer text-xs text-primary">
                          Inspect evidence ({section.evidence.length})
                        </summary>
                        <div className="space-y-3 mt-3">
                          {section.evidence.map((evidence: any, i: number) => {
                            const source = report.sources.find(
                              (s: any) => s.id === evidence.source_id,
                            );
                            return (
                              <blockquote
                                key={i}
                                className="border-l-2 border-primary/40 pl-3 text-xs text-mutedText"
                              >
                                <p>“{evidence.quote}”</p>
                                {source && (
                                  <a
                                    href={source.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-block text-primary mt-2"
                                  >
                                    {source.title} ↗
                                  </a>
                                )}
                              </blockquote>
                            );
                          })}
                        </div>
                      </details>
                    ) : (
                      <p className="text-xs text-amber-300">
                        No supporting quote provided. Treat this section as an
                        open research question.
                      </p>
                    )}
                    {!!section.questions.length && (
                      <ul className="text-xs text-mutedText space-y-2 border-t border-border pt-3">
                        {section.questions.map(
                          (question: string, i: number) => (
                            <li key={i}>Investigate: {question}</li>
                          ),
                        )}
                      </ul>
                    )}
                  </article>
                ))}
              </div>
            </>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {data.sections?.map((section: any, index: number) => (
                <div
                  key={section.id}
                  className="rounded-xl border border-border p-4"
                >
                  <p className="text-[11px] text-primary mb-2">
                    {String(index + 1).padStart(2, "0")} / 12
                  </p>
                  <h3 className="text-sm font-semibold">{section.title}</h3>
                  <p className="text-xs text-mutedText mt-2">
                    Generate to review the supplied evidence and identify what
                    still needs checking.
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </ResourceState>
  );
}
