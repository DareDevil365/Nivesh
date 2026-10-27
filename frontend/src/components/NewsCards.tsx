"use client";

import { useEffect, useState } from "react";
import { dateTime } from "@/lib/research";

export type NewsItem = {
  id: string;
  title: string;
  url: string;
  publisher: string;
  published_at: string;
  excerpt?: string;
  why_read?: string;
  question?: string;
  section?: string;
  evidence_status?: string;
  headline_form?: string;
  reading_order?: number;
  saved?: boolean;
  read?: boolean;
};

export function useReadingList() {
  const [entries, setEntries] = useState<Record<string, NewsItem>>({});
  const [storageNote, setStorageNote] = useState("");
  useEffect(() => {
    try {
      const parsed = JSON.parse(
        localStorage.getItem("nivesh-reading-list:v1") || "{}",
      );
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        setEntries(
          Object.fromEntries(
            Object.entries(parsed)
              .filter(
                ([, value]: any) =>
                  value &&
                  typeof value.id === "string" &&
                  typeof value.publisher === "string" &&
                  typeof value.published_at === "string" &&
                  typeof value.title === "string" &&
                  typeof value.url === "string" &&
                  /^https?:\/\//.test(value.url),
              )
              .slice(-300),
          ) as Record<string, NewsItem>,
        );
      }
    } catch {
      setStorageNote(
        "Reading-list storage is unavailable. Export your list before leaving.",
      );
    }
  }, []);
  const change = (item: NewsItem, key: "saved" | "read") => {
    setEntries((previous) => {
      const updated = {
        ...previous,
        [item.id]: {
          ...item,
          ...previous[item.id],
          [key]: !previous[item.id]?.[key],
        },
      };
      const bounded = Object.fromEntries(Object.entries(updated).slice(-300));
      try {
        localStorage.setItem("nivesh-reading-list:v1", JSON.stringify(bounded));
      } catch {
        setStorageNote(
          "Changes are in memory only. Export your list before leaving.",
        );
      }
      return bounded;
    });
  };
  return { entries, change, storageNote };
}

export function NewsCard({
  item,
  entry,
  onChange,
}: {
  item: NewsItem;
  entry?: NewsItem;
  onChange: (item: NewsItem, key: "saved" | "read") => void;
}) {
  return (
    <article
      className="rounded-xl border border-border bg-surface p-4 space-y-3 min-w-0"
      aria-label={item.title}
    >
      <p className="text-xs text-primary">
        {item.reading_order ? `Read ${item.reading_order} · ` : ""}
        {item.section || item.publisher}
      </p>
      <h3 className="font-semibold leading-relaxed break-words">
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="hover:text-primary"
        >
          {item.title} ↗
        </a>
      </h3>
      <p className="text-xs text-mutedText">
        {item.publisher} · Published {dateTime(item.published_at)} IST
      </p>
      {item.headline_form && item.headline_form !== "reported_headline" && (
        <p className="text-xs text-amber-300">
          Headline suggests{" "}
          {item.headline_form === "stock_picks"
            ? "investment ideas / stock picks"
            : "analysis, opinion or a question"}
          ; article content has not been classified.
        </p>
      )}
      {item.excerpt && (
        <p className="text-sm text-mutedText whitespace-pre-wrap break-words">
          {item.excerpt}
        </p>
      )}
      {item.why_read && (
        <div className="rounded-lg bg-bg p-3 text-xs space-y-2">
          <p>
            <span className="text-primary">Why read: </span>
            {item.why_read}
          </p>
          <p className="text-mutedText">
            <span className="text-neutralText">Ask: </span>
            {item.question}
          </p>
        </div>
      )}
      <p className="text-[11px] text-mutedText">
        {item.evidence_status === "community_claim_unverified"
          ? "Community claim · unverified. Read the full discussion and check original evidence."
          : "Reported headline · article body and financial implications not verified."}
      </p>
      <div className="flex flex-wrap gap-4 text-xs">
        <button
          aria-pressed={!!entry?.saved}
          className="text-primary"
          onClick={() => onChange(item, "saved")}
        >
          {entry?.saved ? "Saved" : "Save for later"}
        </button>
        <button
          aria-pressed={!!entry?.read}
          className="text-mutedText"
          onClick={() => onChange(item, "read")}
        >
          {entry?.read ? "Read ✓" : "Mark as read"}
        </button>
      </div>
    </article>
  );
}

export function FeedStatus({ data }: { data: any }) {
  return (
    <div className="text-xs text-mutedText space-y-1" role="status">
      <p>
        {data.provider || "Public feed"} · {data.status?.replaceAll("_", " ")}
        {data.cached ? " · cached" : ""}
        {data.stale ? " · STALE: showing a previous check" : ""}
        {data.fetched_at ? ` · Checked ${dateTime(data.fetched_at)} IST` : ""}
      </p>
      {data.message && <p className="text-amber-300">{data.message}</p>}
      {data.status === "no_matches" && (
        <p>
          No matching headlines in the checked feed and date window. This does
          not establish that nothing happened.
        </p>
      )}
    </div>
  );
}
