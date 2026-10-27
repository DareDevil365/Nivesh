"use client";
import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import { useResource, EmptyState, ResourceState } from "@/lib/research";
export default function StockChart({
  ticker,
}: {
  ticker: string;
  bars?: unknown[];
}) {
  const [period, setPeriod] = useState("1y");
  const [overlay, setOverlay] = useState("SMA_50");
  const [bollinger, setBollinger] = useState(false);
  const [showRsi, setShowRsi] = useState(false);
  const rsiContainer = useRef<HTMLDivElement>(null);
  const container = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const resource = useResource(
    `/api/companies/${encodeURIComponent(ticker)}/chart?period=${period}`,
  );
  const [error, setError] = useState("");
  const data = resource.data;
  useEffect(() => {
    if (
      !container.current ||
      !data?.bars?.length ||
      resource.error ||
      resource.loading
    )
      return;
    setError("");
    let observer: ResizeObserver | null = null;
    let chart: IChartApi | null = null;
    let rsiChart: IChartApi | null = null;
    try {
      chart = createChart(container.current, {
        width: container.current.clientWidth,
        height: 310,
        layout: {
          background: { type: ColorType.Solid, color: "#131B18" },
          textColor: "#8FA096",
        },
        grid: {
          vertLines: { color: "#1F2B26" },
          horzLines: { color: "#1F2B26" },
        },
        timeScale: { borderColor: "#223028" },
        rightPriceScale: { borderColor: "#223028" },
      });
      chartRef.current = chart;
      const candles = chart.addCandlestickSeries({
        upColor: "#2ECC71",
        downColor: "#E74C3C",
        borderVisible: false,
        wickUpColor: "#2ECC71",
        wickDownColor: "#E74C3C",
      });
      const bars = data.bars.filter((b: any) =>
        [b.open, b.high, b.low, b.close].every(
          (v: number) => Number.isFinite(v) && v > 0,
        ),
      );
      candles.setData(
        bars.map((b: any) => ({
          time: b.time as Time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        })),
      );
      if (overlay) {
        const line = chart.addLineSeries({
          color: "#C9A227",
          lineWidth: 1,
          title: overlay.replace("_", " "),
        });
        line.setData(
          bars
            .filter((b: any) => Number.isFinite(b[overlay]))
            .map((b: any) => ({ time: b.time as Time, value: b[overlay] })),
        );
      }
      if (bollinger) {
        for (const [key, title] of [
          ["BBU_20_2.0", "Bollinger upper"],
          ["BBL_20_2.0", "Bollinger lower"],
        ]) {
          const band = chart.addLineSeries({
            color: "#7398D4",
            lineWidth: 1,
            title,
          });
          band.setData(
            bars
              .filter((bar: any) => Number.isFinite(bar[key]))
              .map((bar: any) => ({ time: bar.time as Time, value: bar[key] })),
          );
        }
      }
      const volume = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      volume
        .priceScale()
        .applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
      volume.setData(
        bars.map((b: any) => ({
          time: b.time as Time,
          value: b.volume,
          color: b.close >= b.open ? "#2ECC7144" : "#E74C3C44",
        })),
      );
      chart.timeScale().fitContent();
      if (showRsi && rsiContainer.current) {
        rsiChart = createChart(rsiContainer.current, {
          width: rsiContainer.current.clientWidth,
          height: 145,
          layout: {
            background: { type: ColorType.Solid, color: "#131B18" },
            textColor: "#8FA096",
          },
          grid: {
            vertLines: { color: "#1F2B26" },
            horzLines: { color: "#1F2B26" },
          },
          rightPriceScale: { borderColor: "#223028", scaleMargins: { top: 0, bottom: 0 } },
          timeScale: { borderColor: "#223028" },
        });
        const rsi = rsiChart.addLineSeries({
          color: "#B99EE8",
          lineWidth: 1,
          title: "RSI 14",
          autoscaleInfoProvider: () => ({
            priceRange: { minValue: 0, maxValue: 100 },
          }),
        });
        for (const price of [30, 70])
          rsi.createPriceLine({
            price,
            color: "#8FA096",
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
          });
        // Preserve matching time indexes even where RSI is still warming up.
        rsi.setData(
          bars.map((bar: any) =>
            Number.isFinite(bar.RSI_14)
              ? { time: bar.time as Time, value: bar.RSI_14 }
              : { time: bar.time as Time },
          ),
        );
        rsiChart.timeScale().fitContent();
        let synchronizing = false;
        const synchronize = (source: IChartApi, target: IChartApi) =>
          source.timeScale().subscribeVisibleLogicalRangeChange((range) => {
            if (synchronizing || !range) return;
            synchronizing = true;
            target.timeScale().setVisibleLogicalRange(range);
            synchronizing = false;
          });
        synchronize(chart, rsiChart);
        synchronize(rsiChart, chart);
      }
      observer = new ResizeObserver((entries) => {
        if (entries[0]?.contentRect.width) {
          chart?.applyOptions({ width: entries[0].contentRect.width });
          rsiChart?.applyOptions({ width: entries[0].contentRect.width });
        }
      });
      observer.observe(container.current);
    } catch {
      setError(
        "The chart could not be rendered. Try another range or reload the data.",
      );
    }
    return () => {
      observer?.disconnect();
      chart?.remove();
      rsiChart?.remove();
      chartRef.current = null;
    };
  }, [data, overlay, bollinger, showRsi, resource.error, resource.loading]);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {[
          ["1mo", "1M"],
          ["6mo", "6M"],
          ["1y", "1Y"],
          ["3y", "3Y"],
          ["5y", "5Y"],
          ["max", "Max"],
        ].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setPeriod(key)}
            className={`rounded border px-2.5 py-1.5 text-xs ${period === key ? "border-primary text-primary" : "border-border text-mutedText"}`}
          >
            {label}
          </button>
        ))}
        <select
          aria-label="Chart overlay"
          value={overlay}
          onChange={(e) => setOverlay(e.target.value)}
          className="bg-bg border border-border rounded p-1.5 text-xs"
        >
          <option value="">No moving average</option>
          {["SMA_20", "SMA_50", "SMA_200", "EMA_20", "EMA_50", "EMA_200"].map(
            (k) => (
              <option key={k} value={k}>
                {k.replace("_", " ")}
              </option>
            ),
          )}
        </select>
        <label className="text-xs text-mutedText flex gap-2 items-center">
          <input
            type="checkbox"
            checked={bollinger}
            onChange={(e) => setBollinger(e.target.checked)}
          />
          Bollinger bands
        </label>
        <label className="text-xs text-mutedText flex gap-2 items-center">
          <input
            type="checkbox"
            checked={showRsi}
            onChange={(e) => setShowRsi(e.target.checked)}
          />
          RSI 14
        </label>
      </div>
      <ResourceState resource={resource}>
        {data?.bars?.length ? (
          <div className="space-y-3">
            <div
              ref={container}
              className="w-full min-w-0"
              style={{ height: 310 }}
            />
            {showRsi && (
              <div>
                <p className="text-[11px] text-mutedText mb-1">
                  RSI 14 · reference levels 30 / 70
                </p>
                <div ref={rsiContainer} style={{ height: 145 }} />
              </div>
            )}
          </div>
        ) : (
          <EmptyState title="Price history unavailable">
            {data?.message ||
              "Choose another range or retry when the provider is available."}
          </EmptyState>
        )}
      </ResourceState>
      {error && (
        <p role="alert" className="text-xs text-negative">
          {error}
        </p>
      )}
      <p className="text-[11px] text-mutedText">
        Daily OHLCV adjusted for splits and dividends by the provider. Moving
        averages, RSI 14 and Bollinger bands (20 sessions, ±2 population
        standard deviations) require their full window; shorter histories may
        have no overlay.
      </p>
    </div>
  );
}
