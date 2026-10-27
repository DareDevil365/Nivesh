"use client";
import { useEffect, useState } from "react";
import { money, number } from "@/lib/research";
export default function DCFCalculator({
  currentPrice,
  ticker,
  fcfPerShare,
}: {
  currentPrice: number;
  ticker: string;
  fcfPerShare?: number | null;
}) {
  const [fcf, setFcf] = useState(
    fcfPerShare == null ? "" : String(fcfPerShare),
  );
  const [growth, setGrowth] = useState(10);
  const [discount, setDiscount] = useState(11);
  const [terminal, setTerminal] = useState(4);
  useEffect(() => {
    setFcf(fcfPerShare == null ? "" : String(fcfPerShare));
  }, [fcfPerShare, ticker]);
  const base = Number(fcf);
  const valid =
    fcf.trim() !== "" &&
    Number.isFinite(base) &&
    base > 0 &&
    discount > terminal;
  const r = discount / 100,
    g = growth / 100,
    t = terminal / 100;
  const value = valid
    ? Array.from(
        { length: 5 },
        (_, i) => (base * (1 + g) ** (i + 1)) / (1 + r) ** (i + 1),
      ).reduce((a, b) => a + b, 0) +
      (base * (1 + g) ** 5 * (1 + t)) / (r - t) / (1 + r) ** 5
    : null;
  return (
    <section className="rounded-card border border-border p-5 space-y-5">
      <h3 className="font-semibold">Build a cash flow valuation scenario</h3>
      <p className="text-xs text-mutedText leading-relaxed">
        Starts with reported annual operating cash flow less capex per current
        share when available. Change the input to test your own normalized cash
        flow. This simplified equity scenario does not forecast debt issuance,
        dilution or working-capital changes.
      </p>
      <label className="block text-sm">
        Annual FCF per share (₹)
        <input
          aria-label="Annual FCF per share"
          type="number"
          min="0.01"
          step="0.01"
          value={fcf}
          onChange={(e) => setFcf(e.target.value)}
          className="block mt-2 bg-bg border border-border rounded-lg p-2 w-full max-w-sm"
        />
      </label>
      <p className="text-xs text-mutedText">
        Reported baseline: {money(fcfPerShare)}. Positive cash flow is required;
        no baseline is inferred from the market price.
      </p>
      <div className="grid sm:grid-cols-3 gap-5">
        {[
          {
            label: "Five-year FCF growth",
            value: growth,
            set: setGrowth,
            min: -20,
            max: 40,
          },
          {
            label: "Discount rate",
            value: discount,
            set: setDiscount,
            min: 5,
            max: 25,
          },
          {
            label: "Terminal growth",
            value: terminal,
            set: setTerminal,
            min: 0,
            max: 8,
          },
        ].map((s) => (
          <label key={s.label} className="text-xs text-mutedText">
            {s.label}: <strong className="text-neutralText">{s.value}%</strong>
            <input
              aria-label={s.label}
              className="block w-full mt-3 accent-primary"
              type="range"
              min={s.min}
              max={s.max}
              step="0.5"
              value={s.value}
              onChange={(e) => s.set(Number(e.target.value))}
            />
          </label>
        ))}
      </div>
      {!valid ? (
        <p role="status" className="text-sm text-amber-300">
          Enter positive FCF per share and keep the discount rate above terminal
          growth.
        </p>
      ) : (
        <div className="rounded-lg bg-bg p-4 space-y-1">
          <p className="text-xs text-mutedText">
            Scenario present value per share
          </p>
          <p className="text-3xl text-primary">{money(value)}</p>
          <p className="text-xs text-mutedText">
            Current price {money(currentPrice)} · Scenario difference{" "}
            {number((value! / currentPrice - 1) * 100, "%")}. This is an
            assumption-driven estimate.
          </p>
        </div>
      )}
    </section>
  );
}
