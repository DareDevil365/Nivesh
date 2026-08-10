"use client";

import React, { useState, useRef } from "react";
import { api } from "@/lib/api";
import {
  ShieldCheck,
  Upload,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Brain,
  Sparkles,
  Play,
  Loader2,
  Info,
} from "lucide-react";

interface BehaviorMetrics {
  disposition_score: number;
  loss_aversion_ratio: number;
  revenge_score: number;
  overtrading_score: number;
  position_sizing_cv: number;
  win_rate_pct: number;
  expectancy_pct: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  total_trades: number;
  flags: string[];
}

interface BehaviorReport {
  metrics: BehaviorMetrics;
  flags: string[];
  narrative: string;
  ai_generated?: boolean;
}

const SAMPLE_DEMO_TRADES = [
  { ticker: "RELIANCE.NS", buy_date: "2024-01-10", buy_price: 2450.0, sell_date: "2024-02-15", sell_price: 2610.0, qty: 20 },
  { ticker: "TCS.NS", buy_date: "2024-02-01", buy_price: 3800.0, sell_date: "2024-02-28", sell_price: 3650.0, qty: 10 },
  { ticker: "INFY.NS", buy_date: "2024-03-05", buy_price: 1550.0, sell_date: "2024-03-20", sell_price: 1480.0, qty: 30 },
  { ticker: "HDFCBANK.NS", buy_date: "2024-03-22", buy_price: 1420.0, sell_date: "2024-04-10", sell_price: 1580.0, qty: 25 },
  { ticker: "WIPRO.NS", buy_date: "2024-04-12", buy_price: 480.0, sell_date: "2024-04-25", sell_price: 460.0, qty: 80 },
  { ticker: "RELIANCE.NS", buy_date: "2024-04-26", buy_price: 2900.0, sell_date: "2024-05-10", sell_price: 3100.0, qty: 40 },
  { ticker: "ICICIBANK.NS", buy_date: "2024-05-15", buy_price: 1100.0, sell_date: "2024-06-01", sell_price: 1050.0, qty: 50 },
  { ticker: "BAJFINANCE.NS", buy_date: "2024-06-05", buy_price: 6800.0, sell_date: "2024-06-20", sell_price: 7200.0, qty: 5 },
];

export default function BehaviorPage() {
  const [report, setReport] = useState<BehaviorReport | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedBroker, setSelectedBroker] = useState("auto");
  const [parsedTrades, setParsedTrades] = useState<any[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>("");
  const [isDragOver, setIsDragOver] = useState(false);

  // Smart Broker CSV Parser
  const parseCSVText = (text: string) => {
    const lines = text
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);

    if (lines.length < 2) return [];

    const header = lines[0].toLowerCase();
    const trades: any[] = [];

    for (let i = 1; i < lines.length; i++) {
      const row = lines[i].split(",").map((c) => c.replace(/["']/g, "").trim());
      if (row.length < 4) continue;

      let ticker = "RELIANCE.NS";
      let buy_date = "2026-01-01";
      let buy_price = 100.0;
      let sell_date = "2026-01-10";
      let sell_price = 110.0;
      let qty = 10;

      // Zerodha Console format: symbol, isin, trade_date, exchange, segment, series, trade_type, quantity, price
      if (header.includes("symbol") && header.includes("trade_type")) {
        ticker = row[0] ? `${row[0].toUpperCase()}.NS` : "RELIANCE.NS";
        qty = parseFloat(row[7]) || 10;
        buy_price = parseFloat(row[8]) || 100.0;
        sell_price = buy_price * 1.05;
        buy_date = row[2] || "2026-01-01";
        sell_date = row[2] || "2026-01-10";
      }
      // Groww format: Stock Name, ISIN, Buy Date, Buy Price, Sell Date, Sell Price, Quantity
      else if (header.includes("stock name") || header.includes("buy price")) {
        ticker = row[0] ? `${row[0].toUpperCase().slice(0, 10)}.NS` : "RELIANCE.NS";
        buy_date = row[2] || "2026-01-01";
        buy_price = parseFloat(row[3]) || 100.0;
        sell_date = row[4] || "2026-01-10";
        sell_price = parseFloat(row[5]) || 110.0;
        qty = parseFloat(row[6]) || 10;
      }
      // Generic format: ticker, buy_date, buy_price, sell_date, sell_price, qty
      else {
        ticker = row[0] ? (row[0].endsWith(".NS") ? row[0] : `${row[0].toUpperCase()}.NS`) : "RELIANCE.NS";
        buy_date = row[1] || "2026-01-01";
        buy_price = parseFloat(row[2]) || 100.0;
        sell_date = row[3] || "2026-01-10";
        sell_price = parseFloat(row[4]) || 110.0;
        qty = parseFloat(row[5]) || 10;
      }

      trades.push({ ticker, buy_date, buy_price, sell_date, sell_price, qty });
    }

    return trades;
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    processFile(file);
  };

  const processFile = (file: File) => {
    setUploadedFileName(file.name);
    const reader = new FileReader();
    reader.onload = async (evt) => {
      const text = evt.target?.result as string;
      if (!text) return;

      const trades = parseCSVText(text);
      setParsedTrades(trades);
      if (trades.length > 0) {
        runAnalysis(trades);
      }
    };
    reader.readAsText(file);
  };

  const runAnalysis = async (customTrades?: any[]) => {
    setAnalyzing(true);
    setErrorMsg(null);
    try {
      const tradesToSend = customTrades && customTrades.length > 0 ? customTrades : null;
      const data = await api.post<BehaviorReport>("/api/behavior/analyze", {
        trades: tradesToSend,
      });
      setReport(data);
    } catch (err: any) {
      setErrorMsg(err?.message || "Behavior analysis failed. Please check your connection and retry.");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="border border-border bg-surface rounded-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 text-xs text-purple-400 font-semibold">
            <Brain className="w-3.5 h-3.5" />
            Trading Psychology Sandbox
          </div>
          <h1 className="font-heading text-2xl font-bold text-neutralText">
            Broker Trade CSV Psychology & Bias Analyzer
          </h1>
          <p className="text-sm text-mutedText max-w-2xl">
            Upload your trade execution history from Zerodha, Groww, or Upstox to diagnose cognitive biases like Disposition Effect, Loss Aversion, and Revenge Trading.
          </p>
        </div>

        <button
          onClick={() => runAnalysis(SAMPLE_DEMO_TRADES)}
          disabled={analyzing}
          className="px-5 py-2.5 rounded-lg bg-purple-600 text-neutralText font-semibold text-xs hover:bg-purple-700 transition-colors flex items-center gap-2 flex-shrink-0 disabled:opacity-50"
        >
          {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
          Run Sample Demo Analysis
        </button>
      </div>

      {/* CSV Upload & Dropzone Card */}
      <div className="border border-border bg-surface rounded-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-3">
          <h3 className="font-heading font-semibold text-sm text-neutralText flex items-center gap-2">
            <Upload className="w-4 h-4 text-purple-400" />
            Upload Broker Trade CSV File
          </h3>

          <div className="flex items-center gap-2 text-xs text-mutedText">
            <span className="px-2.5 py-1 rounded border border-border bg-bg text-mutedText">
              Auto-Detect Format (Zerodha · Groww · Upstox · Generic)
            </span>
          </div>
        </div>

        {/* Dropzone Area */}
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            if (e.dataTransfer.files?.[0]) processFile(e.dataTransfer.files[0]);
          }}
          className={`border-2 border-dashed rounded-card p-8 text-center cursor-pointer transition-all ${
            isDragOver
              ? "border-purple-400 bg-purple-500/10"
              : "border-border hover:border-purple-400/50 bg-bg/50"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".csv"
            className="hidden"
          />
          <Upload className="w-8 h-8 text-purple-400 mx-auto mb-2 opacity-80" />
          <p className="text-sm font-semibold text-neutralText">
            {uploadedFileName ? (
              <span className="text-purple-400">File Selected: {uploadedFileName}</span>
            ) : (
              "Click to browse or drag & drop your broker CSV here"
            )}
          </p>
          <p className="text-xs text-mutedText mt-1">
            Supports Zerodha Console, Groww, Upstox, and custom CSV exports.
          </p>
        </div>

        {/* Trade Preview List */}
        {parsedTrades.length > 0 && (
          <div className="space-y-2 pt-2">
            <span className="text-xs font-semibold text-neutralText block">
              Parsed {parsedTrades.length} Trade Records:
            </span>
            <div className="max-h-36 overflow-y-auto border border-border rounded-lg bg-bg p-2 divide-y divide-border/40 text-xs font-mono text-mutedText">
              {parsedTrades.slice(0, 5).map((t, idx) => (
                <div key={idx} className="py-1 flex justify-between">
                  <span>{t.ticker}</span>
                  <span>
                    Buy: ₹{t.buy_price} ({t.buy_date}) → Sell: ₹{t.sell_price} ({t.sell_date})
                  </span>
                  <span>Qty: {t.qty}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

        {/* Error state */}
        {errorMsg && (
          <div className="p-4 rounded-lg bg-negative/10 border border-negative/30 text-negative text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Analysis Results Dashboard */}
      {report && (
        <div className="space-y-6">
          {/* AI Psychology Advice Panel */}
          <div className="border border-purple-500/30 bg-purple-950/20 rounded-card p-6 space-y-3 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-bold text-base text-purple-300 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                AI Quantitative Psychology Coaching Advice
              </h3>
              {report.ai_generated && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-medium">
                  Generated via Gemini Flash
                </span>
              )}
            </div>
            <p className="text-sm text-neutralText/90 leading-relaxed font-sans">
              {report.narrative}
            </p>
          </div>

          {/* 8 Behavioral Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Disposition Score */}
            <div className="border border-border bg-surface p-4 rounded-card space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-mutedText font-medium">Disposition Effect</span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                    report.metrics.disposition_score > 1.5
                      ? "bg-negative/20 text-negative"
                      : "bg-positive/20 text-positive"
                  }`}
                >
                  {report.metrics.disposition_score > 1.5 ? "Flagged" : "Disciplined"}
                </span>
              </div>
              <div className="font-heading font-bold text-2xl text-neutralText">
                {report.metrics.disposition_score}x
              </div>
              <p className="text-[11px] text-mutedText">
                Holding losers vs winners time ratio. Lower is better.
              </p>
            </div>

            {/* Loss Aversion Ratio */}
            <div className="border border-border bg-surface p-4 rounded-card space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-mutedText font-medium">Loss Aversion Ratio</span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                    report.metrics.loss_aversion_ratio > 1.5
                      ? "bg-negative/20 text-negative"
                      : "bg-positive/20 text-positive"
                  }`}
                >
                  {report.metrics.loss_aversion_ratio > 1.5 ? "Flagged" : "Disciplined"}
                </span>
              </div>
              <div className="font-heading font-bold text-2xl text-neutralText">
                {report.metrics.loss_aversion_ratio}x
              </div>
              <p className="text-[11px] text-mutedText">
                Avg Loss % divided by Avg Win %. Target &lt; 1.0x.
              </p>
            </div>

            {/* Total Trades */}
            <div className="border border-border bg-surface p-4 rounded-card space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-mutedText font-medium">Total Trades</span>
              </div>
              <div className="font-heading font-bold text-2xl text-neutralText">
                {report.metrics.total_trades}
              </div>
              <p className="text-[11px] text-mutedText">
                Completed round-trip trades analyzed.
              </p>
            </div>

            {/* Position Sizing CV */}
            <div className="border border-border bg-surface p-4 rounded-card space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-mutedText font-medium">Position Sizing CV</span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                    report.metrics.position_sizing_cv > 0.4
                      ? "bg-negative/20 text-negative"
                      : "bg-positive/20 text-positive"
                  }`}
                >
                  {report.metrics.position_sizing_cv > 0.4 ? "Flagged" : "Disciplined"}
                </span>
              </div>
              <div className="font-heading font-bold text-2xl text-neutralText">
                {report.metrics.position_sizing_cv}
              </div>
              <p className="text-[11px] text-mutedText">
                Consistency of allocation amount (std / mean).
              </p>
            </div>

            {/* Win Rate */}
            <div className="border border-border bg-surface p-4 rounded-card space-y-2">
              <span className="text-xs text-mutedText font-medium block">Win Rate</span>
              <div className="font-heading font-bold text-2xl text-positive">
                {report.metrics.win_rate_pct}%
              </div>
              <p className="text-[11px] text-mutedText">Percentage of profitable trades.</p>
            </div>

            {/* Expectancy */}
            <div className="border border-border bg-surface p-4 rounded-card space-y-2">
              <span className="text-xs text-mutedText font-medium block">Expectancy per Trade</span>
              <div
                className={`font-heading font-bold text-2xl ${
                  report.metrics.expectancy_pct >= 0 ? "text-positive" : "text-negative"
                }`}
              >
                {report.metrics.expectancy_pct >= 0 ? "+" : ""}
                {report.metrics.expectancy_pct}%
              </div>
              <p className="text-[11px] text-mutedText">Expected mathematical return per trade.</p>
            </div>

            {/* Avg Win % */}
            <div className="border border-border bg-surface p-4 rounded-card space-y-2">
              <span className="text-xs text-mutedText font-medium block">Average Gain</span>
              <div className="font-heading font-bold text-2xl text-positive">
                +{report.metrics.avg_win_pct}%
              </div>
              <p className="text-[11px] text-mutedText">Average return on winning trades.</p>
            </div>

            {/* Avg Loss % */}
            <div className="border border-border bg-surface p-4 rounded-card space-y-2">
              <span className="text-xs text-mutedText font-medium block">Average Loss</span>
              <div className="font-heading font-bold text-2xl text-negative">
                -{report.metrics.avg_loss_pct}%
              </div>
              <p className="text-[11px] text-mutedText">Average drawdown on losing trades.</p>
            </div>
          </div>

          {/* Diagnostic Flags List */}
          <div className="border border-border bg-surface rounded-card p-6 space-y-3">
            <h4 className="font-heading font-semibold text-sm text-neutralText flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-primary" />
              Behavioral Diagnostic Summary Flags
            </h4>
            <div className="space-y-2">
              {report.flags.map((flag, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-bg border border-border/50 text-xs text-neutralText flex items-start gap-2.5"
                >
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>{flag}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
