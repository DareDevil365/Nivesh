"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { download } from "@/lib/research";
import {
  cases,
  lessons,
  pitchFields,
  sources,
  strategies,
  terms,
  SourceKey,
} from "@/lib/learning";

const KEY = "nivesh-learning:v1";
type Progress = { completed: string[]; notes: Record<string, string> };
const empty: Progress = { completed: [], notes: {} };
const panel = "rounded-xl border border-border bg-surface p-5 space-y-4";
const button =
  "rounded-lg border border-border px-4 py-2 text-sm hover:border-primary disabled:opacity-50";
const input = "w-full rounded-lg border border-border bg-bg p-3 text-sm";
const defaults = {
  revenue: "1000",
  growth_pct: "10",
  margin_pct: "10",
  shares: "10",
  dilution_pct: "0",
  pe: "15",
  current_price: "150",
};
const labels: Record<keyof typeof defaults, string> = {
  revenue: "Starting revenue (₹ crore)",
  growth_pct: "Revenue growth (%)",
  margin_pct: "Next-period net margin (%)",
  shares: "Starting shares (crore)",
  dilution_pct: "New shares / dilution (%)",
  pe: "Assumed next-period P/E",
  current_price: "Current price (₹)",
};
function Source({ name }: { name: SourceKey }) {
  return (
    <a
      className="text-primary text-xs underline"
      href={sources[name].url}
      target="_blank"
      rel="noopener noreferrer"
    >
      {sources[name].label} ↗
    </a>
  );
}

export default function LearnPage() {
  const [tab, setTab] = useState("path");
  const [progress, setProgress] = useState<Progress>(empty);
  const [ready, setReady] = useState(false);
  const [storageNote, setStorageNote] = useState("");
  const [query, setQuery] = useState("");
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [values, setValues] = useState(defaults);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const saved = JSON.parse(raw);
        if (
          !Array.isArray(saved.completed) ||
          !saved.notes ||
          typeof saved.notes !== "object" ||
          Array.isArray(saved.notes)
        )
          throw new Error("Invalid saved progress");
        setProgress({
          completed: lessons
            .filter((lesson) => saved.completed.includes(lesson.id))
            .map((lesson) => lesson.id),
          notes: Object.fromEntries(
            pitchFields.map(([id]) => [
              id,
              typeof saved.notes[id] === "string"
                ? saved.notes[id].slice(0, 12000)
                : "",
            ]),
          ),
        });
      }
    } catch {
      setStorageNote(
        "Saved learning data could not be read. This session still works; export your work before leaving. The previous stored copy has not been replaced.",
      );
    }
    setReady(true);
  }, []);
  const save = (next: Progress) => {
    setProgress(next);
    if (storageNote) return;
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      setStorageNote(
        "Browser storage is unavailable. Your work remains in this session; export before leaving.",
      );
    }
  };
  const check = (id: string) => {
    const lesson = lessons.find((item) => item.id === id)!;
    if (answers[id] === undefined) {
      setFeedback({ ...feedback, [id]: "Choose an answer first." });
      return;
    }
    const correct = answers[id] === lesson.answer;
    setFeedback({
      ...feedback,
      [id]: `${correct ? "Correct." : "Try again."} ${lesson.explanation}`,
    });
    if (correct && !progress.completed.includes(id))
      save({ ...progress, completed: [...progress.completed, id] });
  };
  const calculate = async (event: React.FormEvent) => {
    event.preventDefault();
    setResult(null);
    setError("");
    setBusy(true);
    try {
      if (
        Object.values(values).some(
          (value) => !value.trim() || !Number.isFinite(Number(value)),
        )
      )
        throw new Error("Enter a finite number in every field.");
      setResult(
        await api.post(
          "/api/learn/scenario",
          Object.fromEntries(
            Object.entries(values).map(([key, value]) => [key, Number(value)]),
          ),
        ),
      );
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const next = lessons.find(
    (lesson) => !progress.completed.includes(lesson.id),
  );
  const tabs = [
    ["path", "Learning path"],
    ["terms", "Finance terms"],
    ["history", "Market history"],
    ["strategies", "Strategies"],
    ["practice", "Practice lab"],
    ["pitch", "Pitch worksheet"],
  ];
  const number = (value: number) =>
    value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <header className="space-y-3">
        <p className="text-primary text-xs uppercase tracking-widest">
          Learn, investigate, explain
        </p>
        <h1 className="text-3xl font-heading font-bold">
          Build your finance research skills.
        </h1>
        <p className="text-mutedText max-w-3xl text-sm">
          A beginner route from understanding a business to defending a stock
          pitch. Original short lessons, source reading and exercises;
          completion records a quiz answer, not mastery or a recommendation.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link className={button} href="/news">
            Read today’s headlines →
          </Link>
          <Link className={button} href="/screener">
            Find companies →
          </Link>
          <button
            className={button}
            disabled={!ready}
            onClick={() =>
              download(
                "nivesh-learning-and-pitch.json",
                JSON.stringify(
                  {
                    version: 1,
                    exported_at: new Date().toISOString(),
                    ...progress,
                  },
                  null,
                  2,
                ),
                "application/json",
              )
            }
          >
            Export learning & pitch
          </button>
        </div>
        <p className="text-xs text-mutedText">
          Progress and worksheet stay in this browser. No AI calls, account or
          API key needed for lessons. Sources checked 14 October 2026;
          historical cases describe past events.
        </p>
      </header>
      {storageNote && (
        <p role="alert" className="text-amber-300 text-sm">
          {storageNote}
        </p>
      )}
      <nav aria-label="Learning sections" className="flex flex-wrap gap-2">
        {tabs.map(([id, title]) => (
          <button
            key={id}
            aria-pressed={tab === id}
            onClick={() => setTab(id)}
            className={`${button} ${tab === id ? "border-primary text-primary bg-primary/10" : ""}`}
          >
            {title}
          </button>
        ))}
      </nav>
      {tab === "path" && (
        <>
          <section className={panel}>
            <h2 className="font-semibold text-lg">Your preparation plan</h2>
            <p className="text-sm" aria-live="polite">
              {ready
                ? `${progress.completed.length}/${lessons.length} checks completed. ${next ? `Next: ${next.title}` : "All checks completed. Revisit the exercises and challenge your pitch."}`
                : "Loading local progress…"}
            </p>
            <ol className="list-decimal pl-5 text-sm text-mutedText space-y-2">
              <li>
                Foundation: lessons 1–3. Explain a business and read its
                statements.
              </li>
              <li>
                Research: lessons 4–6. Compare drivers, news exposure and
                valuation assumptions.
              </li>
              <li>
                Pitch: lessons 7–9. Test risks, compare strategies and defend a
                written thesis.
              </li>
            </ol>
            <p className="text-sm">
              Daily, spend 20 minutes on the reading desk: one broad event, one
              sector story and one original release. Write what changed, who is
              exposed and what you still need to verify. Weekly, update a
              company model and compare actual results with your dated
              assumptions.
            </p>
          </section>
          {lessons.map((lesson) => (
            <article key={lesson.id} className={panel}>
              <div className="flex flex-wrap justify-between gap-2">
                <h2 className="font-semibold text-lg">{lesson.title}</h2>
                <span className="text-xs text-primary">
                  {progress.completed.includes(lesson.id)
                    ? "Check completed · "
                    : ""}
                  ~{lesson.minutes} min including exercise
                </span>
              </div>
              <p className="text-sm text-mutedText leading-relaxed">
                {lesson.note}
              </p>
              <p className="text-sm">
                <strong>Do this:</strong> {lesson.task}
              </p>
              <Source name={lesson.source} />
              <fieldset disabled={!ready} className="space-y-2">
                <legend className="text-sm font-medium mb-2">
                  {lesson.question}
                </legend>
                {lesson.options.map((option, index) => (
                  <label
                    key={option}
                    className="flex gap-2 items-start text-sm cursor-pointer"
                  >
                    <input
                      className="mt-1"
                      type="radio"
                      name={lesson.id}
                      checked={answers[lesson.id] === index}
                      onChange={() => {
                        setAnswers({ ...answers, [lesson.id]: index });
                        setFeedback({ ...feedback, [lesson.id]: "" });
                      }}
                    />
                    {option}
                  </label>
                ))}
              </fieldset>
              <button
                className={button}
                disabled={!ready}
                onClick={() => check(lesson.id)}
              >
                Check answer: lesson {lesson.id}
              </button>
              {feedback[lesson.id] && (
                <p className="text-sm text-primary" role="status">
                  {feedback[lesson.id]}
                </p>
              )}
            </article>
          ))}
        </>
      )}
      {tab === "terms" && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">
            Finance terms, in plain language
          </h2>
          <input
            className={input}
            aria-label="Search finance terms"
            placeholder="Try EPS, inflation, working capital…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="grid md:grid-cols-2 gap-4">
            {terms
              .filter((item) =>
                `${item.term} ${item.meaning}`
                  .toLowerCase()
                  .includes(query.toLowerCase()),
              )
              .map((item) => (
                <article key={item.term} className={panel}>
                  <h3 className="font-semibold">{item.term}</h3>
                  <p className="text-sm text-mutedText">{item.meaning}</p>
                  <Source name={item.source} />
                </article>
              ))}
          </div>
          {!terms.some((item) =>
            `${item.term} ${item.meaning}`
              .toLowerCase()
              .includes(query.toLowerCase()),
          ) && <p>No matching term. Try a broader word.</p>}
        </section>
      )}
      {tab === "history" && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Study what happened before</h2>
          <p className="text-sm text-mutedText">
            Selected cases, not a complete market history. The research
            questions below are exercises; repeating a headline does not imply
            repeating a market outcome.
          </p>
          {cases.map((item) => (
            <article key={item.title} className={panel}>
              <h3 className="font-semibold text-lg">{item.title}</h3>
              <p className="text-sm">
                <strong>Historical record:</strong> {item.happened}
              </p>
              <p className="text-sm text-mutedText">
                <strong>Mechanism to investigate:</strong> {item.mechanism}
              </p>
              <p className="text-sm">
                <strong>Your exercise:</strong> {item.task}
              </p>
              <a
                className="text-primary text-xs underline"
                target="_blank"
                rel="noopener noreferrer"
                href={item.url}
              >
                {item.source} ↗
              </a>
            </article>
          ))}
        </section>
      )}
      {tab === "strategies" && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">
            Strategies and how they fail
          </h2>
          <p className="text-sm text-mutedText">
            These are research approaches, not recommended trades or promised
            returns. Selection, sizing, horizon and review rules still need to
            be specified.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {strategies.map((item) => (
              <article className={panel} key={item.name}>
                <h3 className="text-lg font-semibold">{item.name}</h3>
                <p className="text-sm">{item.idea}</p>
                <p className="text-sm text-mutedText">
                  <strong>Evidence:</strong> {item.evidence}
                </p>
                <p className="text-sm text-amber-200">
                  <strong>Can fail when:</strong> {item.failure}
                </p>
                <p className="text-sm">
                  <strong>Exercise:</strong> {item.task}
                </p>
                <Source name={item.source} />
              </article>
            ))}
          </div>
          <Link href="/backtester" className={`${button} inline-block`}>
            Open the backtester for supported mechanical rules →
          </Link>
          <p className="text-xs text-mutedText">
            The backtester does not implement these six research approaches
            automatically. Check its available rules, data and cost assumptions.
          </p>
        </section>
      )}
      {tab === "practice" && (
        <section className={panel}>
          <h2 className="text-xl font-semibold">
            Earnings, dilution and valuation lab
          </h2>
          <p className="text-sm text-mutedText">
            Hypothetical, one-period non-financial business. Revenue → profit →
            EPS → an assumed price. Change one input at a time; these are your
            assumptions, not live company data or a price prediction.
          </p>
          <form onSubmit={calculate} className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              {(Object.keys(defaults) as (keyof typeof defaults)[]).map(
                (key) => (
                  <label key={key} className="text-sm space-y-2">
                    <span>{labels[key]}</span>
                    <input
                      className={input}
                      required
                      type="number"
                      step="any"
                      disabled={busy}
                      value={values[key]}
                      onChange={(event) => {
                        setValues({ ...values, [key]: event.target.value });
                        setResult(null);
                        setError("");
                      }}
                    />
                  </label>
                ),
              )}
            </div>
            <button className={button} disabled={busy}>
              {busy ? "Calculating…" : "Calculate illustration"}
            </button>
          </form>
          {error && (
            <p role="alert" className="text-red-400 text-sm">
              {error}
            </p>
          )}
          {result && (
            <div aria-live="polite" className="space-y-3">
              <dl className="grid sm:grid-cols-2 gap-3 text-sm">
                {[
                  ["Next revenue (₹ crore)", result.revenue],
                  ["Net profit (₹ crore)", result.profit],
                  ["Shares (crore)", result.shares],
                  ["Simplified EPS (₹)", result.eps],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-mutedText">{label}</dt>
                    <dd className="text-lg">{number(value)}</dd>
                  </div>
                ))}
              </dl>
              {result.scenario_price === null ? (
                <p>
                  P/E valuation is not applicable to zero or negative earnings.
                  No scenario price is produced.
                </p>
              ) : (
                <p className="text-primary">
                  Assumed scenario price: ₹{number(result.scenario_price)} ·
                  change: {number(result.price_change_pct)}%
                </p>
              )}
              <p className="text-xs text-mutedText">{result.assumptions}</p>
            </div>
          )}
          <p className="text-xs text-mutedText">
            Arithmetic: revenue × (1 + growth); profit = revenue × margin;
            shares × (1 + dilution); EPS = profit ÷ shares; price = positive EPS
            × assumed P/E. Try 20% dilution with unchanged profit. A 50% price
            fall needs a 100% gain to recover.
          </p>
        </section>
      )}
      {tab === "pitch" && (
        <section className={panel}>
          <h2 className="text-xl font-semibold">
            Your college stock-pitch worksheet
          </h2>
          <p className="text-sm text-mutedText">
            One draft in this browser; export before starting another. Filling
            boxes does not verify evidence. Cite original sources and include
            gaps. Exports include your text; review before sharing.
          </p>
          {pitchFields.map(([id, label]) => (
            <label key={id} className="block text-sm space-y-2">
              <span>{label}</span>
              <textarea
                aria-label={label}
                rows={3}
                maxLength={12000}
                disabled={!ready}
                className={input}
                value={progress.notes[id] || ""}
                onChange={(event) =>
                  save({
                    ...progress,
                    notes: { ...progress.notes, [id]: event.target.value },
                  })
                }
              />
            </label>
          ))}
          <p className="text-xs text-mutedText">
            {pitchFields.filter(([id]) => progress.notes[id]?.trim()).length}/
            {pitchFields.length} fields contain notes. This measures draft
            coverage only.
          </p>
        </section>
      )}
    </div>
  );
}
