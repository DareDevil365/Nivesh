"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Network, ArrowRight, ArrowLeft, Loader2, Factory, Store, Info } from "lucide-react";

interface SupplyChainNode {
  ticker?: string;
  name: string;
  category: string;
  relationship: string;
}

interface SupplyChainData {
  ticker: string;
  name: string;
  sector: string;
  upstream_suppliers: SupplyChainNode[];
  downstream_customers: SupplyChainNode[];
  data_source?: string;
  message?: string;
  annual_report_url?: string;
}

export default function SupplyChainGraph({ ticker }: { ticker: string }) {
  const [data, setData] = useState<SupplyChainData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSupplyChain() {
      setLoading(true);
      try {
        const res = await api.get<SupplyChainData>(`/api/companies/${ticker}/supply-chain`);
        setData(res);
      } catch (err) {
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchSupplyChain();
  }, [ticker]);

  if (loading) {
    return (
      <div className="h-48 border border-border bg-surface rounded-card flex items-center justify-center gap-2 text-mutedText text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Mapping Supply Chain & Value Chain Ecosystem…
      </div>
    );
  }

  if (!data) return null;

  // Honest unavailable state — no fabricated data
  if (data.data_source === "unavailable" || (!data.upstream_suppliers.length && !data.downstream_customers.length)) {
    const symbolBare = data.ticker.replace(".NS", "").replace(".BO", "");
    return (
      <div className="border border-border bg-surface rounded-card p-8 space-y-4">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-primary" />
          <h3 className="font-heading font-semibold text-base text-neutralText">Supply Chain & Value Chain Ecosystem</h3>
        </div>
        <div className="flex items-start gap-3 p-4 bg-bg border border-border/60 rounded-lg">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-2 text-xs text-mutedText">
            <p className="leading-relaxed">{data.message || `Detailed supply chain mapping is not yet available for ${symbolBare}.`}</p>
            <p className="font-semibold text-neutralText/80">
              Currently mapped: RELIANCE · TCS · TATAMOTORS
            </p>
            {data.annual_report_url && (
              <a
                href={data.annual_report_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 mt-1 px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20 text-primary font-semibold hover:bg-primary/20 transition-colors"
              >
                <ArrowRight className="w-3.5 h-3.5" />
                View Annual Report on NSE
              </a>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-border bg-surface rounded-card p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-4">
        <div>
          <h3 className="font-heading font-semibold text-base text-neutralText flex items-center gap-2">
            <Network className="w-4 h-4 text-primary" />
            Supply Chain & Value Chain Ecosystem Map
          </h3>
          <p className="text-xs text-mutedText mt-0.5">
            Upstream suppliers (raw materials & components) ──► Target Stock ──► Downstream buyers & distribution.
          </p>
        </div>
        <span className="text-xs text-primary font-bold px-2.5 py-1 rounded bg-primary/10 border border-primary/20">
          Value Chain Graph
        </span>
      </div>

      {/* 3-Column Ecosystem Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-7 gap-4 items-center">
        {/* Column 1: Upstream Suppliers (2 cols) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-wide border-b border-border pb-1.5">
            <Factory className="w-3.5 h-3.5" />
            Upstream Suppliers ({data.upstream_suppliers.length})
          </div>
          <div className="space-y-2">
            {data.upstream_suppliers.map((sup, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-bg border border-border/80 text-xs space-y-1 hover:border-amber-400/40 transition-colors"
              >
                <div className="flex items-center justify-between">
                  {sup.ticker ? (
                    <Link
                      href={`/stock/${sup.ticker}`}
                      className="font-bold text-neutralText hover:text-primary transition-colors font-mono"
                    >
                      {sup.name}
                    </Link>
                  ) : (
                    <span className="font-bold text-neutralText">{sup.name}</span>
                  )}
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 font-semibold border border-amber-500/20">
                    Input
                  </span>
                </div>
                <div className="text-[11px] text-mutedText">{sup.category}</div>
                <div className="text-[10px] text-primary/80 font-medium">{sup.relationship}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Column 2: Connector Arrow Left (1 col on desktop) */}
        <div className="hidden lg:flex flex-col items-center justify-center text-mutedText/40 space-y-1">
          <ArrowRight className="w-6 h-6 text-primary animate-pulse" />
          <span className="text-[9px] font-semibold text-mutedText">Supplies</span>
        </div>

        {/* Column 3: Target Stock Hero Node (1 col on mobile, 1 col on desktop) */}
        <div className="p-5 rounded-card bg-primary/10 border-2 border-primary/40 text-center space-y-2 relative shadow-lg">
          <span className="text-[10px] uppercase font-bold text-positive tracking-widest">Target Stock</span>
          <div className="font-heading font-bold text-xl text-neutralText">{data.name}</div>
          <div className="font-mono text-xs text-primary font-semibold">{data.ticker}</div>
          <div className="text-[11px] text-mutedText">{data.sector}</div>
        </div>

        {/* Column 4: Connector Arrow Right (1 col on desktop) */}
        <div className="hidden lg:flex flex-col items-center justify-center text-mutedText/40 space-y-1">
          <ArrowRight className="w-6 h-6 text-primary animate-pulse" />
          <span className="text-[9px] font-semibold text-mutedText">Buys / Distributes</span>
        </div>

        {/* Column 5: Downstream Customers (2 cols) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-secondary uppercase tracking-wide border-b border-border pb-1.5">
            <Store className="w-3.5 h-3.5" />
            Downstream Buyers ({data.downstream_customers.length})
          </div>
          <div className="space-y-2">
            {data.downstream_customers.map((cust, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-bg border border-border/80 text-xs space-y-1 hover:border-secondary/40 transition-colors"
              >
                <div className="flex items-center justify-between">
                  {cust.ticker ? (
                    <Link
                      href={`/stock/${cust.ticker}`}
                      className="font-bold text-neutralText hover:text-primary transition-colors font-mono"
                    >
                      {cust.name}
                    </Link>
                  ) : (
                    <span className="font-bold text-neutralText">{cust.name}</span>
                  )}
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-secondary/10 text-secondary font-semibold border border-secondary/20">
                    Buyer
                  </span>
                </div>
                <div className="text-[11px] text-mutedText">{cust.category}</div>
                <div className="text-[10px] text-positive font-medium">{cust.relationship}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="px-6 py-2.5 text-[10px] text-mutedText flex items-center gap-1.5 bg-bg/50 rounded-lg">
        <Info className="w-3.5 h-3.5 text-secondary flex-shrink-0" />
        <span>
          Cross-asset supply chain mapping surfaces raw material price ripple effects and client concentration risks before quarterly earnings reports.
        </span>
      </div>
    </div>
  );
}
