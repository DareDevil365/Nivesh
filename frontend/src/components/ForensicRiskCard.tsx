"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ShieldAlert, ShieldCheck, AlertTriangle, RefreshCw, Loader2, Info } from "lucide-react";

interface ForensicData {
  ticker: string;
  altman_z: {
    score: number;
    zone: string;
    status: string;
    description: string;
  };
  beneish_m: {
    score: number;
    flagged: boolean;
    status: string;
    description: string;
  };
  cash_conversion_cycle: {
    ccc_days: number;
    dio_days: number;
    dso_days: number;
    dpo_days: number;
  };
  promoter_pledge: {
    pledged_pct: number;
    label: string;
    status: string;
    description: string;
  };
}

export default function ForensicRiskCard({ ticker }: { ticker: string }) {
  const [data, setData] = useState<ForensicData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchForensic() {
      setLoading(true);
      try {
        const res = await api.get<ForensicData>(`/api/companies/${ticker}/forensic`);
        setData(res);
      } catch (err) {
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchForensic();
  }, [ticker]);

  if (loading) {
    return (
      <div className="h-44 border border-border bg-surface rounded-card flex items-center justify-center gap-2 text-mutedText text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Analyzing Forensic Accounting & Solvency Risk…
      </div>
    );
  }

  if (!data) {
    return (
      <div className="border border-border bg-surface rounded-card p-8 text-center space-y-3">
        <ShieldAlert className="w-8 h-8 text-amber-400 mx-auto" />
        <h3 className="font-heading font-semibold text-base text-neutralText">Forensic Data Unavailable</h3>
        <p className="text-xs text-mutedText max-w-sm mx-auto leading-relaxed">
          Forensic accounting scores require balance sheet and income statement data.
          This stock may have insufficient financial history available from the exchange provider.
        </p>
        <p className="text-[11px] text-mutedText">
          Try a large-cap stock like RELIANCE, TCS, or HDFCBANK for forensic analysis.
        </p>
      </div>
    );
  }

  const { altman_z, beneish_m, cash_conversion_cycle, promoter_pledge } = data;

  return (
    <div className="border border-border bg-surface rounded-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-secondary" />
          <h3 className="font-heading font-semibold text-base text-neutralText">
            Forensic Accounting & Solvency Risk Engine
          </h3>
        </div>
        <span className="text-[11px] text-mutedText bg-bg px-2.5 py-0.5 rounded border border-border">
          Ind AS Accounting Diagnostics
        </span>
      </div>

      {/* Grid of 4 Key Checks */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border border-b border-border">
        {/* 1. Altman Z'-Score */}
        <div className="p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-semibold text-mutedText">Altman Z'-Score</span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                altman_z.status === "positive"
                  ? "bg-positive/20 text-positive"
                  : altman_z.status === "neutral"
                  ? "bg-amber-500/20 text-amber-400"
                  : "bg-negative/20 text-negative"
              }`}
            >
              {altman_z.zone}
            </span>
          </div>
          <div className="font-heading font-bold text-2xl text-neutralText">
            {altman_z.score}
          </div>
          <p className="text-[11px] text-mutedText leading-snug">
            {altman_z.description}
          </p>
        </div>

        {/* 2. Beneish M-Score */}
        <div className="p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-semibold text-mutedText">Beneish M-Score</span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                !beneish_m.flagged ? "bg-positive/20 text-positive" : "bg-negative/20 text-negative"
              }`}
            >
              {!beneish_m.flagged ? "Clean Accruals" : "Manipulation Flag"}
            </span>
          </div>
          <div className="font-heading font-bold text-2xl text-neutralText">
            {beneish_m.score}
          </div>
          <p className="text-[11px] text-mutedText leading-snug">
            {beneish_m.description}
          </p>
        </div>

        {/* 3. Cash Conversion Cycle */}
        <div className="p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-semibold text-mutedText">Cash Conversion Cycle</span>
            <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-primary/20 text-primary">
              Working Capital
            </span>
          </div>
          <div className="font-heading font-bold text-2xl text-neutralText">
            {cash_conversion_cycle.ccc_days} Days
          </div>
          <p className="text-[11px] text-mutedText leading-snug">
            DIO {cash_conversion_cycle.dio_days}d + DSO {cash_conversion_cycle.dso_days}d - DPO {cash_conversion_cycle.dpo_days}d
          </p>
        </div>

        {/* 4. Promoter Pledge Check */}
        <div className="p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-semibold text-mutedText">Promoter Pledge</span>
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                promoter_pledge.status === "positive"
                  ? "bg-positive/20 text-positive"
                  : promoter_pledge.status === "neutral"
                  ? "bg-amber-500/20 text-amber-400"
                  : "bg-negative/20 text-negative"
              }`}
            >
              {promoter_pledge.label}
            </span>
          </div>
          <div className="font-heading font-bold text-2xl text-neutralText">
            {promoter_pledge.pledged_pct}%
          </div>
          <p className="text-[11px] text-mutedText leading-snug">
            {promoter_pledge.description}
          </p>
        </div>
      </div>

      <div className="px-6 py-2.5 text-[10px] text-mutedText flex items-center gap-1.5 bg-bg/50">
        <Info className="w-3.5 h-3.5 text-secondary flex-shrink-0" />
        <span>
          Altman Z'-Score &gt; 2.90 indicates safe solvency. Beneish M-Score &lt; -1.78 confirms clean accounting. Pledged shares &gt; 25% represents margin-call risk.
        </span>
      </div>
    </div>
  );
}
