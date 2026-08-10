"use client";

import React, { useEffect, useState } from "react";
import {
  Brain, FileText, ExternalLink, AlertCircle,
  ShieldCheck, MessageSquare, CheckCircle2, XCircle, MinusCircle, Loader2,
} from "lucide-react";
import { api } from "@/lib/api";

interface ResearchNotes {
  ticker: string;
  symbol_bare: string;
  announcements: any[];
  concall_digest: {
    covered: boolean;
    quarter: string | null;
    management_tone: string | null;
    key_takeaways: string[];
    source_url: string;
    message?: string;
  };
  rule_based_flags: Array<{ type: string; label: string; text: string; status: string }>;
  ai_derived_flags: Array<{ type: string; label: string; text: string; status: string }>;
  official_exchange_filings_url: string;
  bse_announcements_url: string;
  data_source: string;
}

interface ResearchDigestCardProps {
  ticker: string;
}

function FlagItem({ flg }: { flg: { label: string; text: string; status: string } }) {
  const isPos = flg.status === "positive";
  const isNeg = flg.status === "negative";
  return (
    <div
      className={`flex items-start gap-2.5 p-2.5 rounded-lg border text-xs ${
        isPos
          ? "bg-positive/8 border-positive/20"
          : isNeg
          ? "bg-negative/8 border-negative/20"
          : "bg-bg border-border"
      }`}
    >
      {isPos ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-positive shrink-0 mt-0.5" />
      ) : isNeg ? (
        <XCircle className="w-3.5 h-3.5 text-negative shrink-0 mt-0.5" />
      ) : (
        <MinusCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
      )}
      <div>
        <span className={`font-semibold ${isPos ? "text-positive" : isNeg ? "text-negative" : "text-amber-400"}`}>
          {flg.label}:{" "}
        </span>
        <span className="text-neutralText/90">{flg.text}</span>
      </div>
    </div>
  );
}

export default function ResearchDigestCard({ ticker }: ResearchDigestCardProps) {
  const [notes, setNotes] = useState<ResearchNotes | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchNotes() {
      setLoading(true);
      try {
        const data = await api.get<ResearchNotes>(`/api/companies/${ticker}/research-notes`);
        setNotes(data);
      } catch (err) {
        // No fake fallback — show real error state
        setNotes(null);
      } finally {
        setLoading(false);
      }
    }
    fetchNotes();
  }, [ticker]);

  if (loading) {
    return (
      <div className="h-48 bg-surface border border-border rounded-card flex items-center justify-center gap-2 text-mutedText text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Loading Research Digest…
      </div>
    );
  }

  if (!notes) {
    return (
      <div className="bg-surface border border-border rounded-card p-6 text-center text-mutedText text-sm">
        <AlertCircle className="w-6 h-6 text-amber-400 mx-auto mb-2" />
        <p>Research digest unavailable. Check your network connection.</p>
      </div>
    );
  }

  const { rule_based_flags, concall_digest, official_exchange_filings_url, bse_announcements_url, symbol_bare } = notes;
  const hasFlags = rule_based_flags.length > 0;

  return (
    <div className="space-y-5">
      {/* ── Fundamental Flags ── */}
      <div className="bg-surface border border-border rounded-card p-5 space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-positive" />
          <h4 className="font-heading font-bold text-sm text-neutralText">
            Fundamental Flags
            <span className="ml-2 text-[10px] font-normal text-mutedText">
              (computed from exchange data — no AI guesswork)
            </span>
          </h4>
        </div>

        {hasFlags ? (
          <div className="space-y-2">
            {rule_based_flags.map((flg, idx) => (
              <FlagItem key={idx} flg={flg} />
            ))}
          </div>
        ) : (
          <div className="flex items-start gap-2 p-4 bg-bg rounded-lg border border-border/60 text-xs text-mutedText">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <span>Unable to compute fundamental flags — live price data may be unavailable for this stock.</span>
          </div>
        )}
      </div>

      {/* ── Concall Digest ── */}
      <div className={`bg-surface border rounded-card p-5 space-y-3 ${
        concall_digest.covered ? "border-purple-500/30" : "border-border"
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-purple-400" />
            <h4 className="font-heading font-bold text-sm text-neutralText">
              Conference Call Digest
            </h4>
          </div>
          {concall_digest.covered && concall_digest.management_tone && (
            <span className="text-xs font-bold px-2.5 py-1 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
              Tone: {concall_digest.management_tone}
            </span>
          )}
        </div>

        {concall_digest.covered && concall_digest.key_takeaways.length > 0 ? (
          <>
            <ul className="space-y-2 text-xs text-neutralText">
              {concall_digest.key_takeaways.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 mt-1.5 shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <div className="pt-2 border-t border-border flex items-center justify-between text-[11px]">
              <span className="text-mutedText">Based on official exchange transcripts</span>
              <a
                href={concall_digest.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-purple-400 hover:underline flex items-center gap-1 font-semibold"
              >
                Read Transcript <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <div className="flex items-start gap-2 p-3 bg-bg rounded-lg border border-border/60 text-xs text-mutedText">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <span>{concall_digest.message || "Concall transcript data is not available from the current data source."}</span>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              <a
                href={official_exchange_filings_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline font-semibold"
              >
                View NSE Filings <ExternalLink className="w-3 h-3" />
              </a>
              <span className="text-mutedText">·</span>
              <a
                href={bse_announcements_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline font-semibold"
              >
                BSE Announcements <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        )}
      </div>

      {/* ── AI Flags (shows only if populated) ── */}
      {notes.ai_derived_flags.length > 0 && (
        <div className="bg-surface border border-purple-500/20 rounded-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            <h4 className="font-heading font-bold text-sm text-neutralText">
              AI-Derived Flags
              <span className="ml-2 text-[10px] font-normal text-mutedText">
                (extracted from company documents)
              </span>
            </h4>
          </div>
          <div className="space-y-2">
            {notes.ai_derived_flags.map((flg, idx) => (
              <FlagItem key={idx} flg={flg} />
            ))}
          </div>
        </div>
      )}

      {/* ── Official Filings Links ── */}
      <div className="bg-surface border border-border rounded-card p-5 space-y-3">
        <h4 className="font-heading font-bold text-sm text-neutralText flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          Official Exchange Filings
        </h4>
        <p className="text-xs text-mutedText leading-relaxed">
          Corporate announcements, quarterly results, board meeting notices, credit ratings, and
          annual reports are published directly by the company on the exchanges.
        </p>
        <div className="flex flex-wrap gap-3">
          <a
            href={official_exchange_filings_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-primary/40 text-primary hover:bg-primary/10 transition-colors"
          >
            NSE India <ExternalLink className="w-3 h-3" />
          </a>
          <a
            href={bse_announcements_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-border text-mutedText hover:border-primary/40 hover:text-primary transition-colors"
          >
            BSE India <ExternalLink className="w-3 h-3" />
          </a>
          <a
            href={`https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol=${symbol_bare}`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-border text-mutedText hover:border-primary/40 hover:text-primary transition-colors"
          >
            NSE Disclosures <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
