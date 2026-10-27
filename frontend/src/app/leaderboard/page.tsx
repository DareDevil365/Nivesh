import Link from "next/link";
export default function LeaderboardPage() {
  return (
    <section className="rounded-card border border-border bg-surface p-8 space-y-4">
      <h1 className="font-heading font-bold text-2xl">
        Community publishing is not enabled
      </h1>
      <p className="text-sm text-mutedText">
        Nivesh currently supports private research and browser-saved strategy
        parameters. There is no public strategy submission or ranking service.
      </p>
      <Link href="/backtester" className="text-sm text-primary">
        Open the strategy backtester →
      </Link>
    </section>
  );
}
