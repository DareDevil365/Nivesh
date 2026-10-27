"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { dateTime, download, ResourceState, useResource } from "@/lib/research";

const label = (value: string) => value.replaceAll("_", " ");
const evidenceLink = (url: string, page?: number, archive?: string) =>
  page && !archive ? `${url.split("#")[0]}#page=${page}` : url;
const field = "w-full rounded-lg border border-border bg-bg p-2 text-sm";

function ProjectForm({
  ticker,
  lifecycles,
  item,
  seed,
  onSaved,
  onCancel,
}: {
  ticker: string;
  lifecycles: Record<string, string[]>;
  item?: any;
  seed?: any;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [kind, setKind] = useState(item?.kind || "other");
  const [stage, setStage] = useState(item?.stage || "not_established");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const save = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const expected = String(form.get("expected_date") || "");
    const body = {
      stage,
      source_url: String(form.get("source_url") || ""),
      source_quote: String(form.get("source_quote") || ""),
      source_date: form.get("source_date") || null,
      expected_date: expected || null,
      expected_date_kind: expected ? form.get("expected_date_kind") : null,
      note: String(form.get("note") || ""),
      ...(item
        ? { expected_version: item.version }
        : {
            kind,
            title: String(form.get("title") || ""),
            reference: String(form.get("reference") || ""),
          }),
    };
    setBusy(true);
    setError("");
    try {
      await api.post(
        `/api/companies/${encodeURIComponent(ticker)}/pending-items${item ? `/${item.id}/observations` : ""}`,
        body,
      );
      onSaved();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form
      onSubmit={save}
      className="border border-primary/40 rounded-xl p-4 space-y-3"
    >
      <h4 className="font-semibold">
        {item
          ? `Record a new observation: ${item.title}`
          : "Track a project or decision"}
      </h4>
      <p className="text-xs text-mutedText">
        This is your research record. Quotes and stages are not independently
        verified. No information here is sent to AI.
      </p>
      {!item && (
        <>
          <label className="block text-xs">
            Project title
            <input
              name="title"
              className={field}
              required
              minLength={3}
              maxLength={180}
              defaultValue={seed?.title || ""}
            />
          </label>
          <label className="block text-xs">
            Tender / application / project reference (optional)
            <input name="reference" className={field} maxLength={160} />
          </label>
          <label className="block text-xs">
            Project type
            <select
              aria-label="Project type"
              className={field}
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                setStage("not_established");
              }}
            >
              {Object.keys(lifecycles).map((key) => (
                <option key={key} value={key}>
                  {label(key)}
                </option>
              ))}
            </select>
          </label>
        </>
      )}
      <label className="block text-xs">
        Stage supported by your source
        <select
          aria-label="Stage supported by your source"
          className={field}
          value={stage}
          onChange={(e) => setStage(e.target.value)}
        >
          {(lifecycles[kind] || []).map((key) => (
            <option key={key} value={key}>
              {label(key)}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-xs">
        Source URL (HTTPS)
        <input
          name="source_url"
          type="url"
          className={field}
          required
          maxLength={2048}
          defaultValue={seed?.url || item?.source_url || ""}
        />
      </label>
      <label className="block text-xs">
        Supporting source passage
        <textarea
          aria-label="Supporting source passage"
          name="source_quote"
          className={field}
          required
          minLength={12}
          maxLength={2000}
          rows={4}
          defaultValue={seed?.text || ""}
          placeholder="Paste the exact passage supporting this observation."
        />
      </label>
      <div className="grid sm:grid-cols-2 gap-3">
        <label className="block text-xs">
          Source publication date (optional)
          <input
            name="source_date"
            type="date"
            className={field}
            defaultValue={seed?.published_date || ""}
          />
        </label>
        <label className="block text-xs">
          Expected next milestone date (optional)
          <input
            name="expected_date"
            type="date"
            className={field}
            defaultValue={item?.expected_date || ""}
          />
        </label>
      </div>
      <label className="block text-xs">
        Expected date basis
        <select
          aria-label="Expected date basis"
          name="expected_date_kind"
          className={field}
          defaultValue={item?.expected_date_kind || "researcher_estimate"}
        >
          <option value="researcher_estimate">
            My estimate / review window
          </option>
          <option value="source_stated">Stated in the source</option>
        </select>
      </label>
      <label className="block text-xs">
        What still needs checking?
        <textarea
          aria-label="What still needs checking?"
          name="note"
          className={field}
          rows={2}
          maxLength={2000}
        />
      </label>
      <p className="text-xs text-mutedText">
        Preferred bidder is not a final award. Awarded contract value is not
        revenue or cash. A date passing means review is needed, not that a
        project failed.
      </p>
      {error && (
        <p role="alert" className="text-sm text-red-400">
          {error}
        </p>
      )}
      <div className="flex gap-3">
        <button
          disabled={busy}
          className="rounded-lg bg-primary px-4 py-2 text-bg text-sm"
        >
          {busy ? "Saving…" : "Save observation"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-sm text-mutedText"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function CompanyDevelopmentsPanel({
  ticker,
  collectionVersion,
}: {
  ticker: string;
  collectionVersion?: string;
}) {
  const timeline = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/developments`,
  );
  const pending = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/pending-items`,
  );
  const [view, setView] = useState("timeline");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [limit, setLimit] = useState(8);
  const [editor, setEditor] = useState<any>(null);
  const [error, setError] = useState("");
  const data = timeline.data;
  useEffect(() => {
    timeline.reload();
  }, [collectionVersion, timeline.reload]);
  useEffect(() => {
    setEditor(null);
    setError("");
    setQuery("");
    setLimit(8);
  }, [ticker]);
  const items = (data?.items || []).filter(
    (item: any) =>
      (category === "all" || item.kind === category) &&
      `${item.title} ${item.evidence.map((e: any) => e.text).join(" ")}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const remove = async (item: any) => {
    if (!window.confirm(`Delete "${item.title}" and its observation history?`))
      return;
    try {
      await api.delete(
        `/api/companies/${encodeURIComponent(ticker)}/pending-items/${item.id}?version=${item.version}`,
      );
      pending.reload();
    } catch (failure) {
      setError((failure as Error).message);
    }
  };
  return (
    <section
      className="rounded-xl border border-border p-4 space-y-4"
      aria-label="Company developments and pending projects"
    >
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <h3 className="font-semibold">Developments & pending projects</h3>
          <p className="text-xs text-mutedText mt-1">
            What changed, what remains unknown, and which source to check next.
          </p>
        </div>
        <button
          disabled={!data || !pending.data}
          className="text-primary text-xs disabled:opacity-50"
          onClick={() =>
            download(
              `${ticker}-developments.json`,
              JSON.stringify(
                { ticker, developments: data, projects: pending.data },
                null,
                2,
              ),
              "application/json",
            )
          }
        >
          Export timeline & projects
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {[
          ["timeline", "Disclosure timeline"],
          [
            "pending",
            `My pending projects (${pending.data?.items?.length || 0})`,
          ],
          ["leads", "Possible follow-ups"],
        ].map(([key, title]) => (
          <button
            key={key}
            onClick={() => {
              setView(key);
              setEditor(null);
            }}
            className={`rounded-lg border px-3 py-2 text-xs ${view === key ? "border-primary text-primary" : "border-border text-mutedText"}`}
          >
            {title}
          </button>
        ))}
      </div>
      {view === "timeline" && (
        <ResourceState resource={timeline}>
          {data && (
            <>
              <p className="text-xs text-mutedText">
                Last collection:{" "}
                {data.last_collection_at
                  ? `${dateTime(data.last_collection_at)} IST`
                  : "Not completed"}
                . Refresh research above to check supported sources again.
              </p>
              <p className="text-xs text-mutedText">{data.limitations}</p>
              <div className="grid sm:grid-cols-[1fr_auto] gap-2">
                <input
                  aria-label="Search developments"
                  placeholder="Find an order, company change or report…"
                  className={field}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setLimit(8);
                  }}
                />
                <select
                  aria-label="Development category"
                  className={field}
                  value={category}
                  onChange={(e) => {
                    setCategory(e.target.value);
                    setLimit(8);
                  }}
                >
                  {[
                    "all",
                    "project",
                    "management",
                    "clarification",
                    "financing",
                    "ownership",
                    "reports",
                  ].map((key) => (
                    <option key={key} value={key}>
                      {label(key)}
                    </option>
                  ))}
                </select>
              </div>
              {!items.length && (
                <p className="text-sm text-mutedText">
                  No matching disclosures in the checked sources. This does not
                  establish that no developments occurred.
                </p>
              )}
              {items.slice(0, limit).map((item: any) => (
                <article
                  key={item.id}
                  className="rounded-lg border border-border p-3 space-y-2"
                >
                  <p className="text-xs text-primary">
                    {label(item.kind)} ·{" "}
                    {item.evidence_status === "headline_lead"
                      ? "Headline only — attachment not read"
                      : "Source excerpt — review required"}
                  </p>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-medium hover:text-primary"
                  >
                    {item.title} ↗
                  </a>
                  <p className="text-xs text-mutedText">
                    Published: {item.published_date || "Not supplied"} · First
                    indexed: {dateTime(item.first_seen)} IST
                    {item.evidence_status !== "headline_lead" &&
                    !item.in_current_collection
                      ? " · From an earlier collection"
                      : ""}
                  </p>
                  {!!item.evidence.length && (
                    <details>
                      <summary className="text-xs text-primary cursor-pointer">
                        Read collected passages
                      </summary>
                      {item.evidence.map((e: any) => (
                        <blockquote
                          key={e.id}
                          className="mt-2 border-l border-primary/40 pl-3 text-xs text-mutedText whitespace-pre-wrap break-words"
                        >
                          {e.text}
                          <a
                            href={evidenceLink(
                              item.url,
                              e.page,
                              item.archive_member,
                            )}
                            target="_blank"
                            rel="noreferrer"
                            className="block mt-1 text-primary"
                          >
                            {e.page
                              ? `Physical PDF page ${e.page}${item.archive_member ? " inside the source archive" : ""}`
                              : "Original source"}{" "}
                            ↗
                          </a>
                        </blockquote>
                      ))}
                    </details>
                  )}
                  <p className="text-xs text-mutedText">
                    {item.interpretation}
                    {item.duplicate_content
                      ? " This attachment duplicates already collected content; it is not independent confirmation."
                      : ""}
                  </p>
                </article>
              ))}
              {items.length > limit && (
                <button
                  className="text-primary text-sm"
                  onClick={() => setLimit(limit + 8)}
                >
                  Show more disclosures
                </button>
              )}
              {!!data.event_attempts?.length && (
                <details>
                  <summary className="text-xs cursor-pointer text-mutedText">
                    Additional event attachment coverage
                  </summary>
                  {data.event_attempts.map((attempt: any, i: number) => (
                    <p key={i} className="text-xs mt-2 text-mutedText">
                      <a
                        href={attempt.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary"
                      >
                        Attachment {i + 1} ↗
                      </a>
                      : {attempt.status}
                      {attempt.message ? ` — ${attempt.message}` : ""}
                    </p>
                  ))}
                </details>
              )}
            </>
          )}
        </ResourceState>
      )}
      {view === "leads" && (
        <ResourceState resource={timeline}>
          <>
            <p className="text-xs text-mutedText">
              These are keyword-selected passages about potential future
              milestones. They may describe historical plans or conditions, and
              are not confirmed pending projects.
            </p>
            {!data?.follow_up_leads?.length && (
              <p className="text-sm text-mutedText">
                No potential follow-ups found in the collected passages. You can
                still add a sourced project yourself.
              </p>
            )}
            {(data?.follow_up_leads || []).map((lead: any) => (
              <article
                key={lead.id}
                className="border border-border rounded-lg p-3 space-y-2"
              >
                <a
                  href={evidenceLink(lead.url, lead.page, lead.archive_member)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary text-xs"
                >
                  {lead.title} · {lead.page ? `page ${lead.page}` : "source"} ↗
                </a>
                <p className="text-xs text-mutedText whitespace-pre-wrap break-words">
                  {lead.text}
                </p>
                <p className="text-xs text-mutedText">{lead.note}</p>
                <button
                  className="text-primary text-sm"
                  onClick={() => {
                    setView("pending");
                    setEditor({ seed: lead });
                  }}
                >
                  Review and track this lead
                </button>
              </article>
            ))}
          </>
        </ResourceState>
      )}
      {view === "pending" && (
        <ResourceState resource={pending}>
          {pending.data && (
            <>
              <p className="text-xs text-mutedText">{pending.data.privacy}</p>
              {!editor && (
                <button
                  className="rounded-lg border border-primary px-3 py-2 text-sm text-primary"
                  onClick={() => setEditor({})}
                >
                  Track a project or decision
                </button>
              )}
              {editor && (
                <ProjectForm
                  key={editor.item?.id || editor.seed?.id || "new"}
                  ticker={ticker}
                  lifecycles={pending.data.lifecycles}
                  item={editor.item}
                  seed={editor.seed}
                  onCancel={() => setEditor(null)}
                  onSaved={() => {
                    setEditor(null);
                    pending.reload();
                  }}
                />
              )}
              {error && (
                <p role="alert" className="text-red-400 text-sm">
                  {error}
                </p>
              )}
              {!pending.data.items.length && !editor && (
                <p className="text-sm text-mutedText">
                  No projects tracked yet. Add a disclosed bid, approval
                  application or expansion with its supporting source.
                </p>
              )}
              {pending.data.items.map((item: any) => (
                <article
                  key={item.id}
                  className="rounded-lg border border-border p-3 space-y-2"
                >
                  <h4 className="font-semibold text-sm break-words">
                    {item.title}
                  </h4>
                  <p className="text-primary text-xs">
                    {label(item.kind)} · {label(item.stage)} ·
                    Researcher-supplied observation
                  </p>
                  {item.reference && (
                    <p className="text-xs text-mutedText">
                      Reference: {item.reference}
                    </p>
                  )}
                  {item.expected_date && (
                    <p className="text-xs text-mutedText">
                      Expected milestone: {item.expected_date} ·{" "}
                      {item.expected_date_kind === "source_stated"
                        ? "Source-stated date (not independently verified)"
                        : "Researcher estimate"}
                    </p>
                  )}
                  {item.review_due && (
                    <p className="rounded border border-amber-300/30 p-2 text-xs text-amber-300">
                      Review needed: the expected date has passed. This does not
                      establish a delay, loss or cancellation.
                    </p>
                  )}
                  {item.note && (
                    <p className="text-xs text-mutedText whitespace-pre-wrap break-words">
                      To check: {item.note}
                    </p>
                  )}
                  <details>
                    <summary className="text-xs text-primary cursor-pointer">
                      Observation history ({item.history.length})
                    </summary>
                    {[...item.history].reverse().map((observation: any) => (
                      <div
                        key={observation.version}
                        className="mt-3 border-l border-border pl-3 space-y-1"
                      >
                        <p className="text-xs">
                          {label(observation.stage)} · Recorded{" "}
                          {dateTime(observation.recorded_at)} IST
                        </p>
                        <a
                          href={observation.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary text-xs"
                        >
                          Original source ↗ · Published{" "}
                          {observation.source_date || "Unknown"}
                        </a>
                        <p className="text-xs text-mutedText whitespace-pre-wrap break-words">
                          {observation.source_quote}
                        </p>
                      </div>
                    ))}
                  </details>
                  <div className="flex gap-4">
                    <button
                      onClick={() => setEditor({ item })}
                      className="text-primary text-xs"
                    >
                      Record new observation
                    </button>
                    <button
                      onClick={() => remove(item)}
                      className="text-mutedText text-xs"
                    >
                      Delete project
                    </button>
                  </div>
                </article>
              ))}
            </>
          )}
        </ResourceState>
      )}
    </section>
  );
}
