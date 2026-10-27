"use client";
import Link from "next/link";
import StockSearchInput from "@/components/StockSearchInput";
import SectorHeatmap from "@/components/SectorHeatmap";
const EXAMPLES = [
  ["RELIANCE.NS", "Reliance Industries"],
  ["TCS.NS", "Tata Consultancy Services"],
  ["INFY.NS", "Infosys"],
  ["ICICIBANK.NS", "ICICI Bank"],
  ["SBIN.NS", "State Bank of India"],
  ["ITC.NS", "ITC"],
];
export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="relative overflow-hidden rounded-card bg-surface border border-border p-7 md:p-12">
        <div className="absolute right-0 top-0 w-80 h-80 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative space-y-6 max-w-3xl">
          <p className="text-xs font-semibold text-primary uppercase tracking-[.2em]">
            Indian equity research · Built around evidence
          </p>
          <h1 className="font-heading text-3xl md:text-5xl font-bold leading-tight">
            Understand the business.
            <br />
            <span className="text-positive">Question the numbers.</span>
          </h1>
          <p className="text-sm md:text-base text-mutedText leading-relaxed max-w-2xl">
            Explore company financials, compare industry peers, test a trading
            idea, and keep your research in one workspace. See where every
            number comes from and where the data stops.
          </p>
          <div className="max-w-xl">
            <StockSearchInput
              placeholder="Search company or symbol, e.g. RELIANCE or TCS"
              buttonText="Open research"
            />
          </div>
          <div className="flex flex-wrap gap-3 text-xs">
            <Link
              href="/learn"
              className="rounded-lg border border-primary px-5 py-2.5 text-primary font-semibold"
            >
              Learn to research a stock
            </Link>
            <Link
              href="/news"
              className="rounded-lg border border-primary px-5 py-2.5 text-primary font-semibold"
            >
              Start your daily reading
            </Link>
            <Link
              href="/screener"
              className="rounded-lg bg-primary px-5 py-2.5 text-white font-semibold"
            >
              Explore the screener
            </Link>
            <Link
              href="/watchlist"
              className="rounded-lg border border-border px-5 py-2.5"
            >
              Open your watchlist
            </Link>
          </div>
          <p className="text-[11px] text-mutedText">
            Yahoo Finance quotes may be delayed. No live exchange feed or
            verified filing feed is connected.
          </p>
        </div>
      </section>
      <section className="space-y-4">
        <h2 className="text-xl font-heading font-semibold">
          Start with a company
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {EXAMPLES.map(([ticker, name]) => (
            <Link
              href={`/stock/${ticker}`}
              key={ticker}
              className="rounded-card border border-border bg-surface p-5 hover:border-primary/60 transition-colors"
            >
              <p className="font-semibold text-sm">{name}</p>
              <div className="flex justify-between text-xs mt-2">
                <span className="text-mutedText">{ticker}</span>
                <span className="text-primary">Research →</span>
              </div>
            </Link>
          ))}
        </div>
      </section>
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-heading font-semibold">
            Covered sector snapshot
          </h2>
          <Link href="/screener" className="text-xs text-primary">
            View coverage & filters →
          </Link>
        </div>
        <SectorHeatmap />
      </section>
      <section className="grid md:grid-cols-3 gap-4">
        {[
          [
            "/screener",
            "Find & compare",
            "Filter actual fundamentals, inspect missing inputs and compare companies within their industry.",
          ],
          [
            "/backtester",
            "Test a strategy",
            "Use a visible rule builder, next-open execution, cost assumptions and a downloadable trade log.",
          ],
          [
            "/behavior",
            "Review your trades",
            "Match broker executions with FIFO and inspect recorded returns, holding periods and size patterns.",
          ],
        ].map(([href, title, description]) => (
          <Link
            key={href}
            href={href}
            className="rounded-card border border-border bg-surface p-6 space-y-3 hover:border-primary/60"
          >
            <h3 className="font-semibold">{title}</h3>
            <p className="text-sm text-mutedText leading-relaxed">
              {description}
            </p>
            <p className="text-xs text-primary">Open tool →</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
