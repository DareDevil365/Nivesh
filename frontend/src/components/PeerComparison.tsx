"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Layers, Loader2 } from "lucide-react";

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

export const PeerComparison: React.FC<PeerComparisonProps> = ({ currentTicker }) => {
  const [peers, setPeers] = useState<PeerStock[]>([]);
  const [loading, setLoading] = useState(true);

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
        <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
          <Layers className="w-4 h-4 text-primary" />
          Sector Peer Benchmarking Matrix
        </h3>
        <span className="text-xs text-mutedText">{peers.length} Sector Rivals</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs min-w-[700px]">
          <thead className="bg-bg text-mutedText border-b border-border">
            <tr>
              <th className="p-3">Company Ticker</th>
              <th className="p-3 text-right">Price (₹)</th>
              <th className="p-3 text-right">P/E Ratio</th>
              <th className="p-3 text-right">P/B Ratio</th>
              <th className="p-3 text-right">ROE (%)</th>
              <th className="p-3 text-right">ROCE (%)</th>
              <th className="p-3 text-right">D/E Ratio</th>
              <th className="p-3 text-right">Div Yield (%)</th>
              <th className="p-3 text-right">Snowflake Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {peers.map((p: any) => {
              const isCurrent = p.ticker === currentTicker;
              const priceVal = p.current_price ?? p.price;
              const totalScore = p.snowflake_total ?? p.snowflake_score ?? 0;

              return (
                <tr
                  key={p.ticker}
                  className={`transition-colors ${
                    isCurrent ? "bg-primary/10 font-semibold" : "hover:bg-bg/40"
                  }`}
                >
                  <td className="p-3">
                    <Link
                      href={`/stock/${p.ticker}`}
                      className="text-neutralText hover:text-primary transition-colors flex items-center gap-1.5"
                    >
                      <span className="font-mono">{p.ticker.replace(".NS", "")}</span>
                      {isCurrent && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/30 text-primary font-sans font-bold">
                          Current
                        </span>
                      )}
                    </Link>
                  </td>
                  <td className="p-3 text-right font-mono">
                    {priceVal ? `₹${priceVal.toLocaleString("en-IN")}` : "N/A"}
                  </td>
                  <td className="p-3 text-right font-mono">{p.pe ? `${p.pe}x` : "N/A"}</td>
                  <td className="p-3 text-right font-mono">{p.pb ? `${p.pb}x` : "N/A"}</td>
                  <td className="p-3 text-right font-mono text-positive">
                    {p.roe != null ? `${p.roe}%` : "N/A"}
                  </td>
                  <td className="p-3 text-right font-mono text-positive">
                    {p.roce != null ? `${p.roce}%` : "N/A"}
                  </td>
                  <td className="p-3 text-right font-mono">
                    {p.debt_equity != null ? p.debt_equity : "N/A"}
                  </td>
                  <td className="p-3 text-right font-mono">
                    {p.div_yield != null ? `${p.div_yield}%` : "N/A"}
                  </td>
                  <td className="p-3 text-right">
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-surface border border-border text-secondary font-bold font-mono">
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

