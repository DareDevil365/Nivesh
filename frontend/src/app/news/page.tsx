"use client";

import { useState } from "react";
import Link from "next/link";
import NewsDigestPanel from "@/components/NewsDigestPanel";
import { api } from "@/lib/api";
import { download, ResourceState, useResource } from "@/lib/research";
import {
  FeedStatus,
  NewsCard,
  NewsItem,
  useReadingList,
} from "@/components/NewsCards";

export default function ReadingDesk() {
  const resource = useResource("/api/news/reading-desk");
  const [fresh, setFresh] = useState<any>(null);
  const [tab, setTab] = useState("start");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [topic, setTopic] = useState("");
  const [topicFeed, setTopicFeed] = useState<any>(null);
  const [filter, setFilter] = useState("");
  const reading = useReadingList();
  const data =
    fresh ||
    resource.data ||
    (tab === "saved"
      ? {
          sections: [],
          start_here: [],
          sources: [],
          glossary: [],
          ranking_note:
            "Saved stories remain available when the news service cannot be reached.",
          limitations:
            "This is your local reading list; feed freshness is not being checked.",
        }
      : null);
  const refresh = async () => {
    setBusy(true);
    setError("");
    try {
      setFresh(await api.get("/api/news/reading-desk?refresh=true"));
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const explore = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setTopicFeed(
        await api.get(
          `/api/news/topic?topic=${encodeURIComponent(topic.trim())}`,
        ),
      );
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const selected = data?.sections.find((section: any) => section.id === tab);
  const items: NewsItem[] =
    tab === "saved"
      ? Object.values(reading.entries).filter((item) => item.saved)
      : tab === "start"
        ? data?.start_here || []
        : tab === "explore"
          ? topicFeed?.items || []
          : selected?.items || [];
  const visible = items.filter((item) =>
    `${item.title} ${item.publisher}`
      .toLowerCase()
      .includes(filter.toLowerCase()),
  );
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <header className="flex flex-wrap justify-between gap-4">
        <div>
          <p className="text-primary text-xs uppercase tracking-widest">
            Your daily reading desk
          </p>
          <h1 className="font-heading text-3xl font-bold mt-2">
            Understand what is happening.
          </h1>
          <p className="text-mutedText text-sm mt-3 max-w-2xl">
            World markets, the US, India and the forces behind business. Start
            with a short reading route, follow the original sources, then
            research companies.{" "}
            <Link href="/learn" className="text-primary underline">
              New to finance? Follow the learning path.
            </Link>
          </p>
        </div>
        <div className="flex items-start gap-3">
          <button
            onClick={() => {
              setTab("saved");
              setFilter("");
            }}
            className="rounded-lg border border-border px-4 py-2 text-sm"
          >
            Open saved stories
          </button>
          <button
            onClick={refresh}
            disabled={busy}
            className="rounded-lg border border-primary px-4 py-2 text-sm text-primary disabled:opacity-50"
          >
            {busy ? "Checking feeds…" : "Refresh headlines"}
          </button>
          <button
            onClick={() =>
              download(
                "nivesh-reading-list.json",
                JSON.stringify(Object.values(reading.entries), null, 2),
                "application/json",
              )
            }
            className="rounded-lg border border-border px-4 py-2 text-sm"
          >
            Export reading list
          </button>
        </div>
      </header>
      <NewsDigestPanel />
      {error && (
        <p className="text-red-400 text-sm" role="alert">
          {error}
        </p>
      )}
      {reading.storageNote && (
        <p className="text-amber-300 text-xs">{reading.storageNote}</p>
      )}
      <ResourceState
        resource={{
          ...resource,
          loading: !data && resource.loading,
          error: data ? null : resource.error,
        }}
      >
        {data && (
          <>
            <section className="rounded-xl border border-primary/30 bg-primary/5 p-5 space-y-3">
              <h2 className="font-semibold">
                How to read without getting overwhelmed
              </h2>
              <ol className="grid sm:grid-cols-3 gap-4 text-sm list-decimal pl-5">
                <li>
                  Scan the headline and date. Identify the source and what
                  actually changed.
                </li>
                <li>
                  Open the story. Separate reported facts, opinion and future
                  expectations.
                </li>
                <li>
                  Ask who is exposed, what evidence is missing, and whether it
                  changes your company thesis.
                </li>
              </ol>
              <p className="text-xs text-mutedText">{data.ranking_note}</p>
            </section>
            <nav aria-label="Reading topics" className="flex flex-wrap gap-2">
              {[
                ["start", "Start here"],
                ...data.sections.map((section: any) => [
                  section.id,
                  section.label,
                ]),
                ["explore", "Explore a topic"],
                ["saved", "Reading list"],
                ["sources", "Sources & glossary"],
              ].map(([key, title]: string[]) => (
                <button
                  key={key}
                  aria-pressed={tab === key}
                  onClick={() => {
                    setTab(key);
                    setFilter("");
                  }}
                  className={`rounded-lg border px-3 py-2 text-xs ${tab === key ? "border-primary text-primary" : "border-border text-mutedText"}`}
                >
                  {title}
                </button>
              ))}
            </nav>
            {tab === "start" && (
              <div>
                <h2 className="text-xl font-semibold">
                  A suggested route through today's coverage
                </h2>
                <p className="text-xs text-mutedText mt-2">
                  One story per lens when available, with exact-headline and
                  publisher diversity checks. These are reading suggestions, not
                  a claim to have found every major event. Feeds cover roughly
                  the last three days.
                </p>
                <div className="flex flex-wrap gap-3 mt-3">
                  {data.sections.map((section: any) => (
                    <span
                      key={section.id}
                      className={`text-xs ${["unavailable", "busy"].includes(section.status) ? "text-amber-300" : "text-mutedText"}`}
                    >
                      {section.label}: {section.status.replaceAll("_", " ")}
                      {section.stale ? " (stale)" : ""}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {selected && (
              <div className="space-y-2">
                <h2 className="text-xl font-semibold">{selected.label}</h2>
                <p className="text-sm text-mutedText">{selected.why}</p>
                <p className="text-xs text-primary">Ask: {selected.question}</p>
                <FeedStatus data={selected} />
              </div>
            )}
            {tab === "explore" && (
              <form
                onSubmit={explore}
                className="rounded-xl border border-border p-4 space-y-3"
              >
                <label className="block text-sm">
                  Sector, event or topic
                  <input
                    aria-label="Sector, event or topic"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    required
                    minLength={3}
                    maxLength={100}
                    placeholder="cement demand, oil prices, banking…"
                    className="block w-full mt-2 rounded-lg border border-border bg-bg p-3"
                  />
                </label>
                <button
                  disabled={busy}
                  className="rounded-lg bg-primary text-bg px-4 py-2 text-sm"
                >
                  Find headlines
                </button>
                {topicFeed && <FeedStatus data={topicFeed} />}
              </form>
            )}
            {tab === "sources" ? (
              <section className="grid md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h2 className="font-semibold text-xl">Places to read</h2>
                  <p className="text-xs text-mutedText">
                    These are publisher links, not connected subscriptions. Read
                    headlines here and open the publisher for the article; some
                    require payment or login.
                  </p>
                  {data.sources.map((source: any) => (
                    <a
                      key={source.url}
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="block border border-border rounded-xl p-4"
                    >
                      <span className="text-primary">{source.name} ↗</span>
                      <p className="text-sm text-mutedText mt-1">
                        {source.focus}
                      </p>
                    </a>
                  ))}
                </div>
                <div className="space-y-3">
                  <h2 className="font-semibold text-xl">
                    A small finance glossary
                  </h2>
                  {data.glossary.map((entry: any) => (
                    <details
                      key={entry.term}
                      className="rounded-xl border border-border p-4"
                    >
                      <summary className="cursor-pointer font-medium">
                        {entry.term}
                      </summary>
                      <p className="text-sm text-mutedText mt-2">
                        {entry.meaning}
                      </p>
                    </details>
                  ))}
                  <Link href="/screener" className="block text-primary text-sm">
                    Next: find a company to research →
                  </Link>
                </div>
              </section>
            ) : (
              <>
                <input
                  aria-label="Filter loaded headlines"
                  placeholder="Filter these headlines or publishers…"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="w-full rounded-lg border border-border bg-bg p-3 text-sm"
                />
                {!visible.length && (
                  <p className="rounded-xl border border-border p-5 text-sm text-mutedText">
                    {tab === "saved"
                      ? "Save stories for later to build your reading list."
                      : tab === "explore" && !topicFeed
                        ? "Choose a topic to discover recent coverage."
                        : "No matching headlines loaded. Check the feed status or try another topic; an empty list is not proof that nothing happened."}
                  </p>
                )}
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {visible.map((item) => (
                    <NewsCard
                      key={item.id}
                      item={item}
                      entry={reading.entries[item.id]}
                      onChange={reading.change}
                    />
                  ))}
                </div>
              </>
            )}
            <p className="text-xs text-mutedText">
              {data.limitations} Saved/read markers stay in this browser; export
              before clearing storage.
            </p>
          </>
        )}
      </ResourceState>
    </div>
  );
}
