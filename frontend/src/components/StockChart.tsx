"use client";

import React, { useEffect, useRef, useState } from "react";
import { createChart, ColorType, IChartApi } from "lightweight-charts";
import { Loader2 } from "lucide-react";

interface Bar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  SMA_20?: number;
  SMA_50?: number;
  SMA_200?: number;
  RSI_14?: number;
  "BBL_20_2.0"?: number;
  "BBU_20_2.0"?: number;
}

interface StockChartProps {
  ticker: string;
  /** Optional initial bars — if not provided, component fetches by period */
  bars?: Bar[];
}

const PERIODS = [
  { label: "1M", value: "1m" },
  { label: "6M", value: "6m" },
  { label: "1Y", value: "1y" },
  { label: "3Y", value: "3y" },
  { label: "5Y", value: "5y" },
  { label: "Max", value: "max" },
];

import { api } from "@/lib/api";

export default function StockChart({ ticker, bars: initialBars }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartApiRef = useRef<IChartApi | null>(null);

  const [period, setPeriod] = useState("1y");
  const [bars, setBars] = useState<Bar[]>(initialBars || []);
  const [loading, setLoading] = useState(!initialBars);
  const [chartError, setChartError] = useState(false);

  const [showSMA20, setShowSMA20] = useState(true);
  const [showSMA50, setShowSMA50] = useState(true);
  const [showBB, setShowBB] = useState(false);
  const [showRSI, setShowRSI] = useState(false);

  // ── Fetch bars whenever ticker or period changes ──
  useEffect(() => {
    async function fetchBars() {
      setLoading(true);
      try {
        const data = await api.get<{ bars: Bar[] }>(
          `/api/companies/${encodeURIComponent(ticker)}/chart?period=${period}&interval=1d`
        );
        setBars(data.bars || []);
      } catch {
        setBars([]);
      } finally {
        setLoading(false);
      }
    }
    fetchBars();
  }, [ticker, period]);

  // ── Render / update chart when bars or overlays change ──
  useEffect(() => {
    if (!chartContainerRef.current || bars.length === 0) return;

    // Filter out invalid bars with null/NaN/invalid values
    const validBars = bars.filter((b) =>
      b &&
      b.time &&
      typeof b.open === "number" && !isNaN(b.open) && b.open > 0 &&
      typeof b.high === "number" && !isNaN(b.high) && b.high > 0 &&
      typeof b.low === "number" && !isNaN(b.low) && b.low > 0 &&
      typeof b.close === "number" && !isNaN(b.close) && b.close > 0
    );

    if (validBars.length === 0) {
      setChartError(true);
      return;
    }
    setChartError(false);

    try {
      if (chartApiRef.current) {
        chartApiRef.current.remove();
        chartApiRef.current = null;
      }

      const chart = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "#131B18" },
          textColor: "#8FA096",
        },
        grid: {
          vertLines: { color: "#1F2B26" },
          horzLines: { color: "#1F2B26" },
        },
        width: chartContainerRef.current.clientWidth,
        height: 340,
        timeScale: { borderColor: "#223028", timeVisible: true },
        rightPriceScale: { borderColor: "#223028" },
      });

      chartApiRef.current = chart;

      // Candlesticks
      const candlestickSeries = chart.addCandlestickSeries({
        upColor: "#2ECC71",
        downColor: "#E74C3C",
        borderVisible: false,
        wickUpColor: "#2ECC71",
        wickDownColor: "#E74C3C",
      });

      candlestickSeries.setData(
        validBars.map((b) => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close }))
      );

      // SMA 20
      if (showSMA20) {
        const s = chart.addLineSeries({ color: "#C9A227", lineWidth: 1, title: "SMA 20" });
        s.setData(validBars.filter((b) => typeof b.SMA_20 === "number" && !isNaN(b.SMA_20)).map((b) => ({ time: b.time, value: b.SMA_20! })));
      }

      // SMA 50
      if (showSMA50) {
        const s = chart.addLineSeries({ color: "#3B82F6", lineWidth: 1, title: "SMA 50" });
        s.setData(validBars.filter((b) => typeof b.SMA_50 === "number" && !isNaN(b.SMA_50)).map((b) => ({ time: b.time, value: b.SMA_50! })));
      }

      // SMA 200 (auto-added for 3Y/5Y/Max periods)
      if (period === "3y" || period === "5y" || period === "max") {
        const s = chart.addLineSeries({ color: "#F97316", lineWidth: 1, title: "SMA 200" });
        s.setData(validBars.filter((b) => typeof b.SMA_200 === "number" && !isNaN(b.SMA_200)).map((b) => ({ time: b.time, value: b.SMA_200! })));
      }

      // Bollinger Bands
      if (showBB) {
        const bbU = chart.addLineSeries({ color: "#9333EA", lineWidth: 1, title: "BB Upper" });
        const bbL = chart.addLineSeries({ color: "#9333EA", lineWidth: 1, title: "BB Lower" });
        bbU.setData(validBars.filter((b) => typeof b["BBU_20_2.0"] === "number" && !isNaN(b["BBU_20_2.0"])).map((b) => ({ time: b.time, value: b["BBU_20_2.0"]! })));
        bbL.setData(validBars.filter((b) => typeof b["BBL_20_2.0"] === "number" && !isNaN(b["BBL_20_2.0"])).map((b) => ({ time: b.time, value: b["BBL_20_2.0"]! })));
      }

      // RSI pane
      if (showRSI) {
        const rsiSeries = chart.addLineSeries({
          color: "#E74C3C", lineWidth: 1, title: "RSI 14", priceScaleId: "rsi",
        });
        rsiSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0.05 } });
        rsiSeries.setData(validBars.filter((b) => typeof b.RSI_14 === "number" && !isNaN(b.RSI_14)).map((b) => ({ time: b.time, value: b.RSI_14! })));
      }

      // Volume histogram
      const volumeSeries = chart.addHistogramSeries({
        color: "#1E7A4C",
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.75, bottom: showRSI ? 0.2 : 0 },
      });
      volumeSeries.setData(
        validBars.map((b) => ({ time: b.time, value: b.volume || 0, color: b.close >= b.open ? "#1E7A4C" : "#7C2D25" }))
      );

      chart.timeScale().fitContent();

      const handleResize = () => {
        if (chartContainerRef.current && chartApiRef.current) {
          chartApiRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
      };
      window.addEventListener("resize", handleResize);

      return () => {
        window.removeEventListener("resize", handleResize);
        chartApiRef.current?.remove();
        chartApiRef.current = null;
      };
    } catch (err) {
      console.warn("StockChart render exception caught:", err);
      setChartError(true);
    }
  }, [bars, showSMA20, showSMA50, showBB, showRSI, period]);

  return (
    <div className="w-full space-y-3">
      {/* ── Period selector + overlay toggles ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        {/* Period buttons */}
        <div className="flex items-center gap-1 bg-bg border border-border rounded-lg p-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-2.5 py-1 rounded font-semibold transition-colors ${
                period === p.value
                  ? "bg-primary text-white"
                  : "text-mutedText hover:text-neutralText"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Overlay toggles */}
        <div className="flex items-center gap-1.5">
          <span className="text-mutedText font-medium text-[10px] mr-0.5">Overlays:</span>
          {[
            { label: "SMA 20", active: showSMA20, toggle: () => setShowSMA20(!showSMA20), activeClass: "bg-amber-500/20 text-amber-400 border-amber-500/40" },
            { label: "SMA 50", active: showSMA50, toggle: () => setShowSMA50(!showSMA50), activeClass: "bg-blue-500/20 text-blue-400 border-blue-500/40" },
            { label: "BB", active: showBB, toggle: () => setShowBB(!showBB), activeClass: "bg-purple-500/20 text-purple-400 border-purple-500/40" },
            { label: "RSI", active: showRSI, toggle: () => setShowRSI(!showRSI), activeClass: "bg-rose-500/20 text-rose-400 border-rose-500/40" },
          ].map(({ label, active, toggle, activeClass }) => (
            <button
              key={label}
              onClick={toggle}
              className={`px-2 py-0.5 rounded border text-[10px] font-semibold transition-colors ${
                active
                  ? activeClass
                  : "bg-bg text-mutedText border-border hover:text-neutralText"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Chart or loading ── */}
      <div className="relative w-full rounded-lg overflow-hidden">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg/70 rounded-lg">
            <Loader2 className="w-5 h-5 animate-spin text-primary" />
          </div>
        )}
        {!loading && (bars.length === 0 || chartError) ? (
          <div className="w-full h-[340px] flex items-center justify-center bg-bg rounded-lg text-mutedText text-xs p-4 text-center">
            Price history chart is currently unavailable for {ticker}.
          </div>
        ) : (
          <div ref={chartContainerRef} className="w-full h-[340px]" />
        )}
      </div>
    </div>
  );
}
