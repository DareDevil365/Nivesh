"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ResourceState, useResource } from "@/lib/research";
import { FeedStatus, NewsCard, useReadingList } from "@/components/NewsCards";

export default function CompanyNewsPanel({
  ticker,
  community = false,
}: {
  ticker: string;
  community?: boolean;
}) {
  const endpoint = `/api/companies/${encodeURIComponent(ticker)}/${community ? "community" : "news"}`;
  const resource = useResource(endpoint);
  const [fresh, setFresh] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reading = useReadingList();
  const data = fresh || resource.data;
  const refresh = async () => {
    setBusy(true);
    setError("");
    try {
      setFresh(await api.get(endpoint + "?refresh=true"));
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const feed = community ? data?.reddit : data;
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">
            {community ? "Community discussion" : "Company news"}
          </h2>
          <p className="text-sm text-mutedText mt-2">
            {community
              ? "Public Reddit discussion and an X search shortcut. Opinions remain separate from company evidence."
              : "Recent attributed headlines from free public news search. Read the original story and compare it with disclosures."}
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={busy}
          className="text-sm text-primary"
        >
          {busy ? "Checking…" : "Refresh"}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-red-400 text-sm">
          {error}
        </p>
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
            {community ? (
              <>
                <div className="grid sm:grid-cols-2 gap-3">
                  <a
                    href={data.x.url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl border border-border p-4"
                  >
                    <h3 className="font-semibold">What X is saying ↗</h3>
                    <p className="text-xs text-mutedText mt-2">
                      {data.x.message}
                    </p>
                  </a>
                  <a
                    href={data.reddit_search}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl border border-border p-4"
                  >
                    <h3 className="font-semibold">Search Reddit ↗</h3>
                    <p className="text-xs text-mutedText mt-2">
                      Open r/IndianStockMarket for full threads, comments and
                      other search results.
                    </p>
                  </a>
                </div>
                <p className="text-xs text-mutedText">{data.limitations}</p>
                <h3 className="font-semibold">
                  Recent matching Reddit posts · last 90 days
                </h3>
              </>
            ) : (
              <div className="flex flex-wrap gap-4 text-sm">
                <a
                  href={data.search_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary"
                >
                  Open wider news search ↗
                </a>
                <Link href="/news" className="text-primary">
                  World & market reading desk →
                </Link>
                <span className="text-xs text-mutedText">
                  Company-name matches · last 30 days · relevance needs review
                </span>
              </div>
            )}
            <FeedStatus data={feed} />
            {!feed.items?.length && (
              <p className="text-sm text-mutedText">
                No matching items loaded. This does not establish that no news
                or discussion exists.
              </p>
            )}
            <div className="grid md:grid-cols-2 gap-4">
              {(feed.items || []).map((item: any) => (
                <NewsCard
                  key={item.id}
                  item={item}
                  entry={reading.entries[item.id]}
                  onChange={reading.change}
                />
              ))}
            </div>
            {reading.storageNote && (
              <p className="text-xs text-amber-300">{reading.storageNote}</p>
            )}
          </>
        )}
      </ResourceState>
    </section>
  );
}
