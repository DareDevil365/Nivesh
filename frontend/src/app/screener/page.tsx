"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  useResource,
  ResourceState,
  EmptyState,
  CoverageNote,
  number,
  money,
  csvCell,
  download,
} from "@/lib/research";

export default function ScreenerPage() {
  const [preset, setPreset] = useState("");
  const [sector, setSector] = useState("");
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [applied, setApplied] = useState<Record<string, string>>({});
  const [sort, setSort] = useState("market_cap");
  const [order, setOrder] = useState("desc");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    setSector(new URLSearchParams(window.location.search).get("sector") || "");
  }, []);
  const presets = useResource("/api/screener/presets");
  const path = useMemo(() => {
    const q = new URLSearchParams({ ...applied, sort_by: sort, order });
    if (preset) q.set("preset", preset);
    if (sector) q.set("sector", sector);
    return `/api/screener?${q}`;
  }, [applied, preset, sort, order, sector]);
  const resource = useResource(path);
  const data = resource.data;
  useEffect(() => {
    setPage(1);
  }, [path, search]);
  useEffect(() => {
    if (!data?.coverage?.refreshing) return;
    const timer = setTimeout(resource.reload, 6000);
    return () => clearTimeout(timer);
  }, [data, resource.reload]);
  const rows = (data?.results || []).filter((p: any) =>
    `${p.name} ${p.ticker}`.toLowerCase().includes(search.toLowerCase()),
  );
  const maxPage = Math.max(1, Math.ceil(rows.length / 20));
  const currentPage = Math.min(page, maxPage);
  const exportCsv = () =>
    download(
      "nivesh-screen.csv",
      [
        [
          "Ticker",
          "Company",
          "Sector",
          "Price INR",
          "Market cap INR",
          "PE",
          "PB",
          "ROE %",
          "ROCE %",
          "Debt/equity",
          "Dividend yield %",
          "3yr revenue CAGR %",
          "Fetched at",
        ],
        ...rows.map((s: any) => [
          s.ticker,
          s.name,
          s.sector,
          s.current_price,
          s.market_cap,
          s.pe,
          s.pb,
          s.roe,
          s.roce,
          s.debt_equity,
          s.div_yield,
          s.revenue_growth_3yr,
          s.fetched_at,
        ]),
      ]
        .map((r) => r.map(csvCell).join(","))
        .join("\n"),
      "text/csv",
    );
  const refresh = async () => {
    try {
      await api.post("/api/screener/refresh");
      resource.reload();
      setNotice(
        "Snapshot refresh requested. Coverage will update as records arrive.",
      );
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  const save = async () => {
    setSaving(true);
    let count = 0;
    try {
      for (const s of rows.slice(0, 15)) {
        await api.post("/api/watchlist/item", { ticker: s.ticker });
        count++;
      }
      setNotice(`${count} stocks saved to your watchlist.`);
    } catch (e) {
      setNotice(`${count} saved. ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };
  const filters = [
    ["max_pe", "Maximum P/E"],
    ["min_roe", "Minimum ROE (%)"],
    ["min_roce", "Minimum ROCE (%)"],
    ["max_debt_equity", "Maximum debt/equity"],
    ["min_div_yield", "Minimum dividend yield (%)"],
    ["min_revenue_growth", "Minimum revenue CAGR · 3 yr (%)"],
  ];
  return (
    <div className="space-y-6">
      <section className="rounded-card bg-surface border border-border p-6 space-y-4">
        <p className="text-xs text-primary uppercase tracking-wider">
          Discover & compare
        </p>
        <h1 className="font-heading font-bold text-3xl">Stock screener</h1>
        <p className="text-sm text-mutedText">
          Filter the covered research universe using reported fundamentals.
          Companies with missing inputs are excluded from the corresponding
          filter. Review coverage and source dates before comparing.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={refresh}
            className="bg-primary rounded-lg px-4 py-2 text-xs font-semibold text-white"
            disabled={data?.coverage?.refreshing}
          >
            Refresh market snapshot
          </button>
          <button
            onClick={resource.reload}
            className="border border-border rounded-lg px-4 py-2 text-xs"
          >
            Reload results
          </button>
        </div>
        {notice && (
          <p role="status" className="text-sm text-primary">
            {notice}
          </p>
        )}
      </section>
      <div className="grid lg:grid-cols-[260px_minmax(0,1fr)] gap-5">
        <aside className="bg-surface border border-border rounded-card p-5 space-y-5 self-start">
          <label className="text-xs block">
            Research preset
            <select
              aria-label="Research preset"
              value={preset}
              onChange={(e) => {
                setPreset(e.target.value);
                setApplied({});
                setInputs({});
              }}
              className="w-full mt-2 bg-bg border border-border rounded-lg p-2 text-xs"
            >
              <option value="">All covered stocks</option>
              {Object.entries(presets.data?.presets || {})
                .filter(([id]) => id !== "zero_pledge")
                .map(([id, p]: [string, any]) => (
                  <option key={id} value={id}>
                    {p.name}
                  </option>
                ))}
            </select>
          </label>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              setPreset("");
              setApplied(
                Object.fromEntries(
                  Object.entries(inputs).filter(([, v]) => v.trim() !== ""),
                ),
              );
            }}
          >
            {filters.map(([key, label]) => (
              <label className="text-xs block text-mutedText" key={key}>
                {label}
                <input
                  aria-label={label}
                  type="number"
                  step="any"
                  value={inputs[key] || ""}
                  onChange={(e) =>
                    setInputs({ ...inputs, [key]: e.target.value })
                  }
                  className="w-full mt-1.5 bg-bg border border-border rounded-lg p-2 text-neutralText"
                />
              </label>
            ))}
            <label className="text-xs block text-mutedText">
              Sector
              <input
                aria-label="Sector filter"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                placeholder="Exact provider sector name"
                className="w-full mt-1.5 bg-bg border border-border rounded-lg p-2"
              />
            </label>
            <button
              className="w-full bg-primary rounded-lg py-2 text-xs text-white font-semibold"
              type="submit"
            >
              Apply filters
            </button>
            <button
              className="w-full border border-border rounded-lg py-2 text-xs"
              type="button"
              onClick={() => {
                setInputs({});
                setApplied({});
                setPreset("");
                setSector("");
                setSearch("");
              }}
            >
              Clear filters
            </button>
          </form>
          <p className="text-[11px] text-mutedText">
            Promoter pledge screens are unavailable until verified exchange data
            is connected.
          </p>
        </aside>
        <section className="min-w-0 space-y-4">
          <ResourceState resource={resource}>
            {data && (
              <>
                <CoverageNote coverage={data.coverage} />
                <div className="flex flex-wrap gap-2 items-center">
                  <input
                    aria-label="Search screen results"
                    placeholder="Find a company in these results"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="flex-1 min-w-[180px] bg-surface border border-border rounded-lg p-2 text-xs"
                  />
                  <select
                    aria-label="Sort results"
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                    className="bg-surface border border-border rounded-lg p-2 text-xs"
                  >
                    {[
                      ["market_cap", "Market cap"],
                      ["pe", "P/E"],
                      ["roe", "ROE"],
                      ["roce", "ROCE"],
                      ["div_yield", "Dividend yield"],
                      ["snowflake_total", "Checklist passes"],
                    ].map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label="Sort direction"
                    value={order}
                    onChange={(e) => setOrder(e.target.value)}
                    className="bg-surface border border-border rounded-lg p-2 text-xs"
                  >
                    <option value="desc">Descending</option>
                    <option value="asc">Ascending</option>
                  </select>
                  <button
                    onClick={exportCsv}
                    disabled={!rows.length}
                    className="border border-border rounded-lg p-2 text-xs disabled:opacity-40"
                  >
                    Export {rows.length} results
                  </button>
                  <button
                    onClick={save}
                    disabled={!rows.length || saving}
                    className="border border-border rounded-lg p-2 text-xs disabled:opacity-40"
                  >
                    {saving ? "Saving…" : "Watchlist first 15"}
                  </button>
                </div>
                {!rows.length ? (
                  <EmptyState
                    title={
                      data.coverage.refreshing
                        ? "Collecting company records…"
                        : "No matches in the current snapshot"
                    }
                  >
                    Adjust filters or refresh coverage. Missing values are never
                    treated as zero to pass a screen.
                  </EmptyState>
                ) : (
                  <div className="bg-surface border border-border rounded-card overflow-x-auto">
                    <table className="w-full min-w-[780px] text-xs text-left">
                      <thead>
                        <tr className="text-mutedText">
                          <th className="p-3">Company</th>
                          {[
                            "Price",
                            "Market cap (₹ Cr)",
                            "P/E",
                            "ROE",
                            "ROCE",
                            "D/E",
                            "Yield",
                          ].map((k) => (
                            <th key={k} className="p-3 text-right">
                              {k}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {rows
                          .slice((currentPage - 1) * 20, currentPage * 20)
                          .map((s: any) => (
                            <tr
                              key={s.ticker}
                              className="border-t border-border hover:bg-bg"
                            >
                              <td className="p-3">
                                <Link
                                  href={`/stock/${encodeURIComponent(s.ticker)}`}
                                  className="font-semibold hover:text-primary"
                                >
                                  {s.name}
                                </Link>
                                <p className="text-[10px] text-mutedText mt-1">
                                  {s.ticker} · {s.sector}
                                </p>
                              </td>
                              <td className="p-3 text-right">
                                {money(s.current_price)}
                              </td>
                              {[
                                s.market_cap_cr,
                                s.pe,
                                s.roe,
                                s.roce,
                                s.debt_equity,
                                s.div_yield,
                              ].map((v, i) => (
                                <td key={i} className="p-3 text-right">
                                  {number(v, [2, 3, 5].includes(i) ? "%" : "")}
                                </td>
                              ))}
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <div className="flex justify-between items-center text-xs text-mutedText">
                  <span>
                    {rows.length} matches · Page {currentPage} of {maxPage}
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={currentPage <= 1}
                      onClick={() => setPage(currentPage - 1)}
                      className="p-2 border border-border rounded disabled:opacity-30"
                    >
                      Previous
                    </button>
                    <button
                      disabled={currentPage >= maxPage}
                      onClick={() => setPage(currentPage + 1)}
                      className="p-2 border border-border rounded disabled:opacity-30"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}
          </ResourceState>
        </section>
      </div>
    </div>
  );
}
