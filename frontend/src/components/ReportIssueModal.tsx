"use client";
import { useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/research";
export function ReportIssueModal() {
  const dialog = useRef<HTMLDialogElement>(null);
  const pathname = usePathname();
  const [view, setView] = useState("form");
  const [category, setCategory] = useState("data_inaccuracy");
  const [description, setDescription] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reports, setReports] = useState<any[]>([]);
  const history = async () => {
    setView("history");
    setBusy(true);
    setNotice("");
    try {
      const data = await api.get("/api/reports");
      setReports(data.reports);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setNotice("");
    try {
      await api.post("/api/reports", {
        category,
        description: description.trim(),
        route: pathname,
        ticker: pathname.match(/\/stock\/([^/]+)/)?.[1],
      });
      setNotice(
        "Feedback saved to your workspace. No automatic agent review is scheduled.",
      );
      setDescription("");
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <button
        onClick={() => {
          setView("form");
          setNotice("");
          dialog.current?.showModal();
        }}
        className="fixed bottom-5 right-5 z-40 bg-surface border border-primary/50 rounded-full px-4 py-2 text-xs text-primary shadow-xl"
      >
        Report an issue
      </button>
      <dialog
        ref={dialog}
        aria-labelledby="feedback-title"
        className="w-[calc(100%-2rem)] max-w-lg rounded-card border border-border bg-surface text-neutralText p-6"
      >
        <div className="space-y-5">
          <div className="flex justify-between gap-3">
            <h2
              id="feedback-title"
              className="font-heading font-semibold text-lg"
            >
              Feedback & data issues
            </h2>
            <button
              aria-label="Close feedback"
              onClick={() => dialog.current?.close()}
              className="text-mutedText px-2"
            >
              ✕
            </button>
          </div>
          <p className="text-xs text-mutedText">
            Reports are saved on this server and visible only in this browser
            workspace. Do not include account numbers, passwords or personal
            financial documents.
          </p>
          <div className="flex gap-2 text-xs">
            <button
              onClick={() => setView("form")}
              className="border border-border rounded-lg p-2"
            >
              New report
            </button>
            <button
              onClick={history}
              className="border border-border rounded-lg p-2"
            >
              My reports
            </button>
          </div>
          {notice && (
            <p role="status" className="text-sm text-primary">
              {notice}
            </p>
          )}
          {busy && (
            <p role="status" className="text-sm text-mutedText">
              Working…
            </p>
          )}
          {view === "form" ? (
            <form onSubmit={submit} className="space-y-4">
              <label className="block text-xs" htmlFor="issue-category">
                Category
                <select
                  id="issue-category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="block mt-2 w-full bg-bg border border-border rounded-lg p-2"
                >
                  {[
                    ["data_inaccuracy", "Wrong or missing figure"],
                    ["supply_chain_error", "Relationship data"],
                    ["snowflake_anomaly", "Checklist calculation"],
                    ["chart_visual_bug", "Chart or interface"],
                    ["feature_suggestion", "Feature suggestion"],
                    ["other", "Other issue"],
                  ].map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-xs" htmlFor="issue-description">
                What went wrong?
                <textarea
                  id="issue-description"
                  required
                  minLength={5}
                  maxLength={5000}
                  rows={5}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the issue and include a public source link if a figure is incorrect."
                  className="block mt-2 w-full bg-bg border border-border rounded-lg p-3"
                />
              </label>
              <button
                disabled={busy || description.trim().length < 5}
                className="bg-primary text-white rounded-lg px-4 py-2 text-xs disabled:opacity-40"
              >
                Save report
              </button>
            </form>
          ) : (
            <div className="max-h-72 overflow-y-auto space-y-3">
              {!busy && !reports.length && (
                <p className="text-sm text-mutedText">
                  No reports saved in this workspace.
                </p>
              )}
              {reports.map((r) => (
                <article
                  key={r.id}
                  className="border border-border rounded-lg p-3 space-y-2"
                >
                  <p className="text-[11px] text-mutedText">
                    {dateTime(r.timestamp)} IST · {r.ticker || "General"}
                  </p>
                  <p className="text-sm whitespace-pre-wrap break-words">
                    {r.description}
                  </p>
                </article>
              ))}
            </div>
          )}
        </div>
      </dialog>
    </>
  );
}
