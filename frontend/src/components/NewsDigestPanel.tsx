"use client";

import { useResource, dateTime, download } from "@/lib/research";

export default function NewsDigestPanel() {
  const resource = useResource<{ digest: any }>("/api/news/digest/latest");
  const digest = resource.data?.digest;
  return (
    <section className="rounded-xl border border-primary/30 bg-surface p-5 space-y-3">
      <h2 className="text-lg font-semibold">Your morning brief</h2>
      <p className="text-sm text-mutedText">
        The news bot prepares a source-linked email brief. Locally generated
        copies appear here; cloud email runs do not automatically sync to this
        installation. Headlines and feed excerpts remain labelled separately
        from article excerpts.
      </p>
      {resource.error ? (
        <p role="status" className="text-sm text-amber-300">
          The saved brief could not be loaded.{" "}
          <button onClick={resource.reload} className="text-primary underline">
            Retry
          </button>
        </p>
      ) : resource.loading ? (
        <p className="text-xs text-mutedText">Checking for a saved brief…</p>
      ) : !digest ? (
        <p className="text-xs text-mutedText">
          No brief has been prepared yet. The reading desk below still works
          normally.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap justify-between gap-3">
            <p className="text-sm text-primary">
              {digest.date_ist} · Prepared {dateTime(digest.generated_at)} IST
            </p>
            <button
              className="text-xs text-primary underline"
              onClick={() =>
                download(
                  `nivesh-morning-brief-${digest.date_ist}.json`,
                  JSON.stringify(digest, null, 2),
                  "application/json",
                )
              }
            >
              Export brief
            </button>
          </div>
          <p className="text-xs text-mutedText">
            {digest.coverage.headlines} unique headlines considered ·{" "}
            {digest.coverage.article_excerpts} article excerpts ·{" "}
            {digest.coverage.feed_excerpts} publisher feed excerpts ·{" "}
            {digest.coverage.headline_only} headline only. This is a dated saved
            brief, not a live update.
          </p>
          <details>
            <summary className="cursor-pointer text-primary text-sm">
              Read the saved summary
            </summary>
            <div className="grid md:grid-cols-2 gap-4 mt-4">
              {digest.sections.map((section: any) => (
                <article
                  key={section.id}
                  className="rounded-lg border border-border p-4 space-y-3"
                >
                  <h3 className="font-semibold">{section.label}</h3>
                  {section.bullets.map((bullet: any, index: number) => (
                    <div className="space-y-2 text-sm" key={index}>
                      <p>{bullet.text}</p>
                      <p className="text-mutedText">
                        <strong>Why it may matter:</strong>{" "}
                        {bullet.why_it_matters}
                      </p>
                      <ul className="space-y-1 text-xs">
                        {bullet.sources.map((source: any) => (
                          <li key={source.id}>
                            <a
                              className="text-primary underline"
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {source.publisher}: {source.title} ↗
                            </a>
                            <span className="text-mutedText">
                              {" "}
                              · {source.read_status.replaceAll("_", " ")}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </article>
              ))}
            </div>
            <p className="text-xs text-mutedText mt-4">{digest.limitations}</p>
          </details>
        </>
      )}
    </section>
  );
}
