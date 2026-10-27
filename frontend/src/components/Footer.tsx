import Link from "next/link";
export function Footer() {
  return (
    <footer className="border-t border-border bg-surface mt-12 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
        <div className="flex flex-wrap justify-between gap-4">
          <p className="font-heading font-bold text-sm">
            NIVESH{" "}
            <span className="text-mutedText font-normal">
              · Indian equity research
            </span>
          </p>
          <nav
            aria-label="Footer"
            className="flex flex-wrap gap-4 text-xs text-mutedText"
          >
            {[
              ["/news", "Reading desk"],
              ["/learn", "Learn finance"],
              ["/screener", "Screener"],
              ["/watchlist", "Watchlist"],
              ["/backtester", "Backtester"],
              ["/behavior", "Trade journal"],
            ].map(([href, label]) => (
              <Link href={href} key={href} className="hover:text-primary">
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <p className="text-xs text-mutedText leading-relaxed max-w-4xl">
          Market quotes and financial statements are supplied by Yahoo Finance
          and may be delayed, incomplete or restated. Check the source date and
          verify material figures in company filings. Valuation scenarios and
          backtests depend on their stated assumptions. Research tools do not
          constitute investment advice.
        </p>
        <p className="text-[11px] text-mutedText">
          Watchlists and feedback use a browser workspace on this server.
          Research notes and saved strategy parameters remain in your browser.
          Export copies before clearing browser data.
        </p>
      </div>
    </footer>
  );
}
