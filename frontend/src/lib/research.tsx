"use client";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";

export function useResource<T = any>(path: string | null) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<{
    path: string | null;
    data: T | null;
    error: string | null;
    loading: boolean;
  }>({ path, data: null, error: null, loading: true });
  const reload = useCallback(() => setRevision((n) => n + 1), []);
  useEffect(() => {
    let active = true;
    setState((previous) => ({
      path,
      data: previous.path === path ? previous.data : null,
      error: null,
      loading: !!path && (previous.path !== path || previous.data == null),
    }));
    if (path)
      api
        .get<T>(path)
        .then((data) => {
          if (active) setState({ path, data, error: null, loading: false });
        })
        .catch((error: Error) => {
          if (active)
            setState({
              path,
              data: null,
              error: error.message,
              loading: false,
            });
        });
    return () => {
      active = false;
    };
  }, [path, revision]);
  return {
    data: state.path === path ? state.data : null,
    error: state.path === path ? state.error : null,
    loading: state.path !== path || state.loading,
    reload,
  };
}

export function EmptyState({
  title,
  children,
  retry,
}: {
  title: string;
  children?: ReactNode;
  retry?: () => void;
}) {
  return (
    <div
      className="rounded-card border border-border bg-surface p-6 space-y-3"
      role="status"
    >
      <p className="font-semibold text-neutralText">{title}</p>
      {children && (
        <div className="text-sm text-mutedText leading-relaxed">{children}</div>
      )}
      {retry && (
        <button
          className="rounded-lg border border-primary/40 px-4 py-2 text-xs text-primary"
          onClick={retry}
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function ResourceState({
  resource,
  children,
}: {
  resource: { loading: boolean; error: string | null; reload: () => void };
  children: ReactNode;
}) {
  if (resource.loading)
    return (
      <EmptyState title="Loading research data…">
        Fetching available records from the provider.
      </EmptyState>
    );
  if (resource.error)
    return (
      <EmptyState title="Data could not be loaded" retry={resource.reload}>
        {resource.error}
      </EmptyState>
    );
  return <>{children}</>;
}

export function number(
  value: number | null | undefined,
  suffix = "",
  digits = 2,
) {
  return value == null || !Number.isFinite(value)
    ? "—"
    : `${value.toLocaleString("en-IN", { maximumFractionDigits: digits })}${suffix}`;
}
export function money(value: number | null | undefined) {
  return value == null || !Number.isFinite(value) ? "—" : `₹${number(value)}`;
}
export function dateTime(value?: string | null) {
  if (!value) return "Not supplied";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        dateStyle: "medium",
        timeStyle: "short",
      });
}
export function download(name: string, content: string, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function csvCell(value: unknown) {
  let text = value == null ? "" : String(value);
  if (typeof value === "string" && /^[=+@\-\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}
export interface Coverage {
  covered: number;
  universe: number;
  refreshing: boolean;
  stale?: boolean;
  oldest_fetched_at?: string | null;
  newest_fetched_at?: string | null;
  failed_last_refresh?: number;
  scope?: string;
}
export function CoverageNote({ coverage }: { coverage?: Coverage }) {
  if (!coverage) return null;
  return (
    <div
      className="text-xs text-mutedText bg-bg border border-border rounded-lg p-3 space-y-1"
      role="status"
    >
      <p>
        <strong className="text-neutralText">
          {coverage.covered} of {coverage.universe} bundled symbols covered.
        </strong>{" "}
        {coverage.refreshing
          ? "Refreshing available company data…"
          : coverage.stale
            ? "Snapshot includes older data. Refresh before comparing."
            : "Snapshot coverage"}
      </p>
      <p>
        {coverage.scope}{" "}
        {coverage.newest_fetched_at &&
          `Latest fetch: ${dateTime(coverage.newest_fetched_at)} IST.`}
      </p>
      {!!coverage.failed_last_refresh && (
        <p>
          {coverage.failed_last_refresh} fetches failed in the last refresh.
          Missing companies are excluded.
        </p>
      )}
    </div>
  );
}
