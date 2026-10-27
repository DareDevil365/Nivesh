"use client";
import { number, download, csvCell, EmptyState } from "@/lib/research";
export interface StatementRow {
  metric: string;
  values: (number | null)[];
  unit?: string;
}
export function StatementTable({
  periods,
  rows,
  name,
}: {
  periods: string[];
  rows: StatementRow[];
  name: string;
}) {
  if (!periods.length || !rows.length)
    return (
      <EmptyState title="No statement records available">
        The provider did not supply matching records for this view.
      </EmptyState>
    );
  const exportRows = () =>
    download(
      `${name}.csv`,
      [
        ["Metric", "Unit", ...periods],
        ...rows.map((r) => [r.metric, r.unit, ...r.values]),
      ]
        .map((r) => r.map(csvCell).join(","))
        .join("\n"),
      "text/csv",
    );
  return (
    <div className="space-y-3">
      <button
        onClick={exportRows}
        className="text-xs text-primary border border-border rounded-lg px-3 py-2"
      >
        Export this table
      </button>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] text-xs text-left">
          <thead>
            <tr className="text-mutedText border-b border-border">
              <th className="p-3 sticky left-0 bg-surface">Metric</th>
              <th className="p-3">Unit</th>
              {periods.map((p, i) => (
                <th key={`${p}-${i}`} className="p-3 text-right">
                  {p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.metric}
                className="border-b border-border/50 hover:bg-bg"
              >
                <th className="p-3 font-medium sticky left-0 bg-surface">
                  {r.metric}
                </th>
                <td className="p-3 text-mutedText whitespace-nowrap">
                  {r.unit || "—"}
                </td>
                {periods.map((_, i) => (
                  <td
                    key={i}
                    className="p-3 text-right font-mono whitespace-nowrap"
                  >
                    {number(r.values[i], "", 2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
