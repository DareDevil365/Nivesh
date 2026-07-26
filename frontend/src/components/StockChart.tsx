"use client";

import React, { useEffect, useRef, useState } from "react";
import { createChart, ColorType, IChartApi, ISeriesApi } from "lightweight-charts";

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
  MACD?: number;
  MACD_signal?: number;
  "BBL_20_2.0"?: number;
  "BBU_20_2.0"?: number;
}

interface StockChartProps {
  bars: Bar[];
  ticker: string;
}

export default function StockChart({ bars, ticker }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartApiRef = useRef<IChartApi | null>(null);

  const [showSMA20, setShowSMA20] = useState(true);
  const [showSMA50, setShowSMA50] = useState(true);
  const [showBB, setShowBB] = useState(false);
  const [showRSI, setShowRSI] = useState(false);

  useEffect(() => {
    if (!chartContainerRef.current || !bars || bars.length === 0) return;

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
      height: 380,
      timeScale: {
        borderColor: "#223028",
        timeVisible: true,
      },
      rightPriceScale: {
        borderColor: "#223028",
      },
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
      bars.map((bar) => ({
        time: bar.time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }))
    );

    // SMA 20 Overlay
    if (showSMA20) {
      const sma20Series = chart.addLineSeries({
        color: "#C9A227",
        lineWidth: 1,
        title: "SMA 20",
      });
      sma20Series.setData(
        bars.filter(b => b.SMA_20 !== undefined && b.SMA_20 !== null).map(b => ({ time: b.time, value: b.SMA_20! }))
      );
    }

    // SMA 50 Overlay
    if (showSMA50) {
      const sma50Series = chart.addLineSeries({
        color: "#3B82F6",
        lineWidth: 1,
        title: "SMA 50",
      });
      sma50Series.setData(
        bars.filter(b => b.SMA_50 !== undefined && b.SMA_50 !== null).map(b => ({ time: b.time, value: b.SMA_50! }))
      );
    }

    // Bollinger Bands Overlay
    if (showBB) {
      const bbUpper = chart.addLineSeries({ color: "#9333EA", lineWidth: 1, title: "BBU" });
      const bbLower = chart.addLineSeries({ color: "#9333EA", lineWidth: 1, title: "BBL" });
      bbUpper.setData(bars.filter(b => b["BBU_20_2.0"] !== undefined && b["BBU_20_2.0"] !== null).map(b => ({ time: b.time, value: b["BBU_20_2.0"]! })));
      bbLower.setData(bars.filter(b => b["BBL_20_2.0"] !== undefined && b["BBL_20_2.0"] !== null).map(b => ({ time: b.time, value: b["BBL_20_2.0"]! })));
    }

    // RSI 14 Indicator Pane
    if (showRSI) {
      const rsiSeries = chart.addLineSeries({
        color: "#E74C3C",
        lineWidth: 1,
        title: "RSI 14",
        priceScaleId: "rsi_scale",
      });


      rsiSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0.05 },
      });

      rsiSeries.setData(
        bars
          .filter((b) => b.RSI_14 !== undefined && b.RSI_14 !== null)
          .map((b) => ({ time: b.time, value: b.RSI_14! }))
      );
    }

    // Volume Histogram Overlay
    const volumeSeries = chart.addHistogramSeries({
      color: "#1E7A4C",
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.7, bottom: showRSI ? 0.2 : 0 },
    });

    volumeSeries.setData(
      bars.map((bar) => ({
        time: bar.time,
        value: bar.volume,
        color: bar.close >= bar.open ? "#1E7A4C" : "#7C2D25",
      }))
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current && chartApiRef.current) {
        chartApiRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartApiRef.current) {
        chartApiRef.current.remove();
        chartApiRef.current = null;
      }
    };
  }, [bars, ticker, showSMA20, showSMA50, showBB, showRSI]);

  return (
    <div className="w-full space-y-3">
      {/* Indicator Overlay Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-mutedText font-semibold">Overlays:</span>
          <button
            onClick={() => setShowSMA20(!showSMA20)}
            className={`px-2.5 py-1 rounded border font-semibold transition-colors ${
              showSMA20 ? "bg-amber-500/20 text-amber-400 border-amber-500/30" : "bg-bg text-mutedText border-border"
            }`}
          >
            SMA 20
          </button>
          <button
            onClick={() => setShowSMA50(!showSMA50)}
            className={`px-2.5 py-1 rounded border font-semibold transition-colors ${
              showSMA50 ? "bg-blue-500/20 text-blue-400 border-blue-500/30" : "bg-bg text-mutedText border-border"
            }`}
          >
            SMA 50
          </button>
          <button
            onClick={() => setShowBB(!showBB)}
            className={`px-2.5 py-1 rounded border font-semibold transition-colors ${
              showBB ? "bg-purple-500/20 text-purple-400 border-purple-500/30" : "bg-bg text-mutedText border-border"
            }`}
          >
            Bollinger Bands
          </button>
          <button
            onClick={() => setShowRSI(!showRSI)}
            className={`px-2.5 py-1 rounded border font-semibold transition-colors ${
              showRSI ? "bg-rose-500/20 text-rose-400 border-rose-500/30" : "bg-bg text-mutedText border-border"
            }`}
          >
            RSI (14) Sub-pane
          </button>
        </div>

        <div className="flex items-center gap-1 text-[11px] text-mutedText">
          <span className="w-2 h-2 rounded-full bg-positive inline-block" />
          <span>Volume Spikes Filter Active</span>
        </div>
      </div>


      <div ref={chartContainerRef} className="w-full h-[380px] rounded-lg" />
    </div>
  );
}
