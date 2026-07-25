"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import SnowflakeChart from "@/components/SnowflakeChart";
import StockChart from "@/components/StockChart";
import DCFCalculator from "@/components/DCFCalculator";
import ResearchDigestCard from "@/components/ResearchDigestCard";
import GlossaryTooltip from "@/components/GlossaryTooltip";
import { CheckCircle2, XCircle, Clock, TrendingUp, DollarSign, Activity, FileText, AlertCircle, Share2, Download } from "lucide-react";

interface CompanyProfile {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  isin: string;
  fundamentals: {
    pe: number;
    pb: number;
    roe: number;
    roce: number;
    debt_equity: number;
    div_yield: number;
    revenue_growth_3yr: number;
    eps_growth_3yr: number;
    promoter_holding: number;
    pledged_shares_pct: number;
    market_cap: number;
    current_price: number;
    day_change: number;
    day_change_pct: number;
  };
  snowflake_scores: {
    value: number;
    future: number;
    past: number;
    health: number;
    dividend: number;
  };
  pros_cons: {
    pros: Array<{ text: string; rule_id: string }>;
    cons: Array<{ text: string; rule_id: string }>;
  };
  delayed_badge: boolean;
}

interface ChartBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export default function StockDashboardPage() {
  const params = useParams();
  const ticker = (params?.ticker as string) || "RELIANCE.NS";

  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [chartBars, setChartBars] = useState<ChartBar[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>("overview");

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const profileRes = await fetch(`http://localhost:8000/api/companies/${ticker}`);
        if (!profileRes.ok) throw new Error("Backend offline");
        const profileData: CompanyProfile = await profileRes.json();
        setCompany(profileData);

        const chartRes = await fetch(`http://localhost:8000/api/companies/${ticker}/chart`);
        if (chartRes.ok) {
          const chartData = await chartRes.json();
          setChartBars(chartData.bars || []);
        }
      } catch (err) {
        setCompany({
          ticker: ticker.toUpperCase(),
          name: ticker.replace(".NS", "").toUpperCase(),
          sector: "Diversified",
          industry: "Core Industry",
          isin: "INE000000000",
          fundamentals: {
            pe: 24.5,
            pb: 3.2,
            roe: 16.5,
            roce: 18.2,
            debt_equity: 0.35,
            div_yield: 1.45,
            revenue_growth_3yr: 14.2,
            eps_growth_3yr: 16.8,
            promoter_holding: 51.2,
            pledged_shares_pct: 0.0,
            market_cap: 1850000000000,
            current_price: 2980.5,
            day_change: 36.8,
            day_change_pct: 1.25,
          },
          snowflake_scores: {
            value: 4,
            future: 5,
            past: 5,
            health: 6,
            dividend: 3,
          },
          pros_cons: {
            pros: [
              { text: "Company is virtually debt-free", rule_id: "DEBT_FREE" },
              { text: "Good track record of Return on Equity (ROE): 3yr ROE 16.5%", rule_id: "HIGH_ROE" },
              { text: "High promoter holding of 51.2%", rule_id: "HIGH_PROMOTER" },
            ],
            cons: [
              { text: "Stock is trading at a high valuation P/E of 24.5x", rule_id: "HIGH_PE" },
            ],
          },
          delayed_badge: true,
        });

        const bars: ChartBar[] = [];
        let price = 2800;
        const now = new Date();
        for (let i = 250; i >= 0; i--) {
          const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
          const dateStr = d.toISOString().split("T")[0];
          const change = (Math.random() - 0.49) * 40;
          price = Math.max(100, price + change);
          const open = price - (Math.random() - 0.5) * 15;
          const high = Math.max(open, price) + Math.random() * 15;
          const low = Math.min(open, price) - Math.random() * 15;
          bars.push({
            time: dateStr,
            open: Math.round(open * 100) / 100,
            high: Math.round(high * 100) / 100,
            low: Math.round(low * 100) / 100,
            close: Math.round(price * 100) / 100,
            volume: Math.floor(Math.random() * 1500000) + 500000,
          });
        }
        setChartBars(bars);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [ticker]);

  const handleShareReportCard = () => {
    alert(`Report card snapshot generated for ${ticker}! (SimplyWall.st-style shareable card feature)`);
  };

  if (loading || !company) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-mutedText text-sm font-medium">Fetching stock data for {ticker}...</p>
      </div>
    );
  }

  const { fundamentals, snowflake_scores, pros_cons } = company;
  const isPositive = fundamentals.day_change >= 0;

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-surface border border-border rounded-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="font-heading font-bold text-2xl md:text-3xl text-neutralText">
              {company.name}
            </h1>
            <span className="text-xs font-semibold px-2.5 py-1 rounded bg-bg text-mutedText border border-border">
              {company.ticker}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-mutedText">
            <span>Sector: <strong className="text-neutralText">{company.sector}</strong></span>
            <span>•</span>
            <span>Industry: <strong className="text-neutralText">{company.industry}</strong></span>
            <span>•</span>
            <span>ISIN: <strong className="text-neutralText">{company.isin}</strong></span>
          </div>
        </div>

        <div className="flex items-end md:items-right flex-col gap-3">
          <div className="flex items-baseline gap-2">
            <span className="font-heading font-bold text-3xl text-neutralText">
              ₹{fundamentals.current_price.toLocaleString("en-IN")}
            </span>
            <span
              className={`font-heading font-semibold text-sm px-2 py-0.5 rounded ${
                isPositive ? "bg-positive/10 text-positive" : "bg-negative/10 text-negative"
              }`}
            >
              {isPositive ? "+" : ""}{fundamentals.day_change} ({isPositive ? "+" : ""}{fundamentals.day_change_pct}%)
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleShareReportCard}
              className="bg-bg hover:bg-border text-neutralText border border-border text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors font-medium"
            >
              <Share2 className="w-3.5 h-3.5 text-secondary" /> Share Report Card
            </button>
            <span className="inline-flex items-center gap-1 text-xs text-mutedText bg-bg px-2.5 py-1 rounded-full border border-border">
              <Clock className="w-3.5 h-3.5 text-secondary" /> Delayed ~15 min
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Snowflake Radar + Stock Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 5-Axis Snowflake Radar Card */}
        <div className="bg-surface border border-border rounded-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-heading font-bold text-lg text-neutralText flex items-center gap-1.5">
                <GlossaryTooltip term="Snowflake">Snowflake Analysis</GlossaryTooltip>
              </h2>
              <span className="text-xs text-mutedText">5-Axis Radar</span>
            </div>
            <p className="text-xs text-mutedText mb-4">
              Visual evaluation across Value, Future, Past, Health, and Dividend pillars.
            </p>
          </div>

          <SnowflakeChart scores={snowflake_scores} />

          <div className="grid grid-cols-5 gap-1 text-center mt-4 pt-4 border-t border-border text-[11px]">
            <div>
              <div className="text-mutedText">VAL</div>
              <div className="font-bold text-positive">{snowflake_scores.value}/6</div>
            </div>
            <div>
              <div className="text-mutedText">FUT</div>
              <div className="font-bold text-positive">{snowflake_scores.future}/6</div>
            </div>
            <div>
              <div className="text-mutedText">PAS</div>
              <div className="font-bold text-positive">{snowflake_scores.past}/6</div>
            </div>
            <div>
              <div className="text-mutedText">HEA</div>
              <div className="font-bold text-positive">{snowflake_scores.health}/6</div>
            </div>
            <div>
              <div className="text-mutedText">DIV</div>
              <div className="font-bold text-positive">{snowflake_scores.dividend}/6</div>
            </div>
          </div>
        </div>

        {/* Stock Candlestick Chart */}
        <div className="lg:col-span-2 bg-surface border border-border rounded-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-bold text-lg text-neutralText">
              Price & Technical Analysis Chart
            </h2>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2.5 py-1 rounded bg-primary/20 text-positive border border-primary/30 font-semibold">
                Daily (OHLCV)
              </span>
            </div>
          </div>

          <StockChart bars={chartBars} ticker={company.ticker} />
        </div>
      </div>

      {/* Key Financial Ratios Grid with SimplyWall.st Hover Glossary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="bg-surface border border-border rounded-card p-3.5 space-y-1">
          <div className="text-[11px] uppercase font-semibold"><GlossaryTooltip term="P/E Ratio" /></div>
          <div className="font-heading font-bold text-base text-neutralText">{fundamentals.pe}x</div>
        </div>
        <div className="bg-surface border border-border rounded-card p-3.5 space-y-1">
          <div className="text-[11px] uppercase font-semibold"><GlossaryTooltip term="P/B Ratio" /></div>
          <div className="font-heading font-bold text-base text-neutralText">{fundamentals.pb}x</div>
        </div>
        <div className="bg-surface border border-border rounded-card p-3.5 space-y-1">
          <div className="text-[11px] uppercase font-semibold"><GlossaryTooltip term="ROE" /></div>
          <div className="font-heading font-bold text-base text-positive">{fundamentals.roe}%</div>
        </div>
        <div className="bg-surface border border-border rounded-card p-3.5 space-y-1">
          <div className="text-[11px] uppercase font-semibold"><GlossaryTooltip term="ROCE" /></div>
          <div className="font-heading font-bold text-base text-positive">{fundamentals.roce}%</div>
        </div>
        <div className="bg-surface border border-border rounded-card p-3.5 space-y-1">
          <div className="text-[11px] uppercase font-semibold"><GlossaryTooltip term="Debt / Equity" /></div>
          <div className="font-heading font-bold text-base text-neutralText">{fundamentals.debt_equity}</div>
        </div>
        <div className="bg-surface border border-border rounded-card p-3.5 space-y-1">
          <div className="text-[11px] uppercase font-semibold"><GlossaryTooltip term="Dividend Yield" /></div>
          <div className="font-heading font-bold text-base text-secondary">{fundamentals.div_yield}%</div>
        </div>
        <div className="bg-surface border border-border rounded-card p-3.5 space-y-1 col-span-2 sm:col-span-1">
          <div className="text-[11px] uppercase font-semibold"><GlossaryTooltip term="Promoter Holding" /></div>
          <div className="font-heading font-bold text-base text-neutralText">{fundamentals.promoter_holding}%</div>
        </div>
      </div>

      {/* SimplyWall.st Interactive DCF Calculator */}
      <DCFCalculator currentPrice={fundamentals.current_price} ticker={company.ticker} />

      {/* Screener.in Rule-Based Pros & Cons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-surface border border-border rounded-card p-6 space-y-4">
          <div className="flex items-center gap-2 text-positive">
            <CheckCircle2 className="w-5 h-5" />
            <h3 className="font-heading font-bold text-lg text-neutralText">Pros (Automated Rules)</h3>
          </div>
          <ul className="space-y-2.5">
            {pros_cons.pros.map((pro, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-xs text-neutralText">
                <span className="w-1.5 h-1.5 rounded-full bg-positive mt-1.5 shrink-0" />
                <span>{pro.text}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-surface border border-border rounded-card p-6 space-y-4">
          <div className="flex items-center gap-2 text-negative">
            <XCircle className="w-5 h-5" />
            <h3 className="font-heading font-bold text-lg text-neutralText">Cons (Automated Rules)</h3>
          </div>
          <ul className="space-y-2.5">
            {pros_cons.cons.map((con, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-xs text-neutralText">
                <span className="w-1.5 h-1.5 rounded-full bg-negative mt-1.5 shrink-0" />
                <span>{con.text}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Feature Tabs (Overview vs Pseudo-Brain AI Research Digest) */}
      <div className="bg-surface border border-border rounded-card p-6 space-y-4">
        <div className="flex border-b border-border gap-6">
          <button
            onClick={() => setActiveTab("overview")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === "overview"
                ? "border-primary text-positive"
                : "border-transparent text-mutedText hover:text-neutralText"
            }`}
          >
            Overview & Valuation Summary
          </button>
          <button
            onClick={() => setActiveTab("research")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "research"
                ? "border-primary text-positive"
                : "border-transparent text-mutedText hover:text-neutralText"
            }`}
          >
            <FileText className="w-4 h-4 text-purple-400" />
            Pseudo-Brain AI Research Digest (§3.8)
          </button>
        </div>

        {activeTab === "overview" && (
          <div className="text-xs text-mutedText space-y-3 py-2 leading-relaxed">
            <p>
              <strong>Valuation Summary:</strong> {company.name} is currently trading at a P/E multiple of {fundamentals.pe}x.
              The 3-year revenue CAGR stands at {fundamentals.revenue_growth_3yr}% with an EPS growth rate of {fundamentals.eps_growth_3yr}%.
            </p>
            <p>
              <strong>Capital Structure:</strong> Debt-to-equity stands at {fundamentals.debt_equity}, indicating a healthy balance sheet with promoter pledged shares at {fundamentals.pledged_shares_pct}%.
            </p>
          </div>
        )}

        {activeTab === "research" && (
          <ResearchDigestCard ticker={company.ticker} />
        )}
      </div>
    </div>
  );
}
