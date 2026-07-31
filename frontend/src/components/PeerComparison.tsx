"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Layers, Loader2, ArrowUpDown, ChevronDown, ChevronUp, Check } from "lucide-react";

interface PeerStock {
  ticker: string;
  name: string;
  price: number;
  pe: number;
  pb: number;
  roe: number;
  roce: number;
  debt_equity: number;
  div_yield: number;
  snowflake_score: number;
}

interface PeerComparisonProps {
  currentTicker: string;
}

type SortField = "name" | "price" | "pe" | "pb" | "roe" | "roce" | "debt_equity" | "div_yield" | "snowflake_score";

export const PeerComparison: React.FC<PeerComparisonProps> = ({ currentTicker }) => {
  const [peers, setPeers] = useState<PeerStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortField, setSortField] = useState<SortField>("snowflake_score");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    async function loadPeers() {
      setLoading(true);
      try {
        const res = await api.get<{ ticker: string; peers: PeerStock[] }>(
          `/api/companies/${currentTicker}/peers`
        );
        setPeers(res.peers || []);
      } catch (err) {
        console.error("Failed to load peers", err);
      } finally {
        setLoading(false);
      }
    }
    loadPeers();
  }, [currentTicker]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder(field === "pe" || field === "pb" || field === "debt_equity" ? "asc" : "desc");
    }
  };

  const sortedPeers = [...peers].sort((a, b) => {
    let aVal: any = a[sortField] ?? 0;
    let bVal: any = b[sortField] ?? 0;
    if (typeof aVal === "string") {
      return sortOrder === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
  });

  if (loading) {
    return (
      <div className="w-full h-48 border border-border bg-surface rounded-card flex items-center justify-center text-mutedText text-sm gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        <span>Loading Sector Peer Matrix...</span>
      </div>
    );
  }

  if (!peers || peers.length === 0) return null;

  return (
    <div className="border border-border bg-surface rounded-card p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary" />
            Sector Peer Benchmarking Matrix
          </h3>
          <p className="text-xs text-mutedText mt-0.5">
            Click column headers to sort by metrics. Highlighted row is current stock.
          </p>
        </div>
        <span className="text-xs text-mutedText font-semibold bg-bg px-2.5 py-1 rounded border border-border">
          {peers.length} Competitors
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs min-w-[750px]">
          <thead className="bg-bg text-mutedText border-b border-border">
            <tr>
              {[
                { key: "name", label: "Company" },
                { key: "price", label: "Price (₹)", align: "right" },
                { key: "pe", label: "P/E", align: "right" },
                { key: "pb", label: "P/B", align: "right" },
                { key: "roe", label: "ROE (%)", align: "right" },
                { key: "roce", label: "ROCE (%)", align: "right" },
                { key: "debt_equity", label: "D/E", align: "right" },
                { key: "div_yield", label: "Div Yield (%)", align: "right" },
                { key: "snowflake_score", label: "Snowflake Score", align: "right" },
              ].map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key as SortField)}
                  className={`p-3 cursor-pointer hover:text-neutralText transition-colors select-none ${
                    col.align === "right" ? "text-right" : "text-left"
                  }`}
                >
                  <div className={`inline-flex items-center gap-1 ${col.align === "right" ? "justify-end" : ""}`}>
                    <span>{col.label}</span>
                    {sortField === col.key ? (
                      sortOrder === "asc" ? (
                        <ChevronUp className="w-3 h-3 text-primary" />
                      ) : (
                        <ChevronDown className="w-3 h-3 text-primary" />
                      )
                    ) : (
                      <ArrowUpDown className="w-3 h-3 opacity-40" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {sortedPeers.map((p: any) => {
              const isCurrent = p.ticker === currentTicker;
              const priceVal = p.current_price ?? p.price;
              const totalScore = p.snowflake_total ?? p.snowflake_score ?? 0;

              return (
                <tr
                  key={p.ticker}
                  className={`transition-colors ${
                    isCurrent ? "bg-primary/10 font-semibold border-l-2 border-l-primary" : "hover:bg-bg/40"
                  }`}
                >
                  <td className="p-3">
                    <Link
                      href={`/stock/${p.ticker}`}
                      className="text-neutralText hover:text-primary transition-colors flex items-center gap-1.5"
                    >
                      <span className="font-mono font-bold">{p.ticker.replace(".NS", "").replace(".BO", "")}</span>
                      <span className="text-mutedText font-normal text-[11px] truncate max-w-[150px]">
                        ({p.name || p.ticker})
                      </span>
                      {isCurrent && (
                        <span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.2 rounded font-semibold ml-1">
                          Current
                        </span>
                      )}
                    </Link>
                  </td>
                  <td className="p-3 text-right font-mono">
                    {priceVal ? `₹${priceVal.toLocaleString("en-IN")}` : "N/A"}
                  </td>
                  <td className="p-3 text-right font-mono">
                    {p.pe ? `${p.pe}x` : "N/A"}
                  </td>
                  <td className="p-3 text-right font-mono">
                    {p.pb ? `${p.pb}x` : "N/A"}
                  </td>
                  <td className={`p-3 text-right font-mono ${p.roe > 15 ? "text-positive" : p.roe < 8 ? "text-negative" : ""}`}>
                    {p.roe ? `${p.roe}%` : "N/A"}
                  </td>
                  <td className={`p-3 text-right font-mono ${p.roce > 15 ? "text-positive" : p.roce < 8 ? "text-negative" : ""}`}>
                    {p.roce ? `${p.roce}%` : "N/A"}
                  </td>
                  <td className={`p-3 text-right font-mono ${p.debt_equity < 0.5 ? "text-positive" : p.debt_equity > 1.5 ? "text-negative" : ""}`}>
                    {p.debt_equity != null ? p.debt_equity : "N/A"}
                  </td>
                  <td className="p-3 text-right font-mono text-secondary">
                    {p.div_yield ? `${p.div_yield}%` : "0%"}
                  </td>
                  <td className="p-3 text-right font-mono">
                    <span className={`inline-block px-2 py-0.5 rounded font-bold text-xs ${
                      totalScore >= 18 ? "bg-positive/20 text-positive" : totalScore >= 12 ? "bg-amber-500/20 text-amber-400" : "bg-negative/20 text-negative"
                    }`}>
                      {totalScore}/30
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
