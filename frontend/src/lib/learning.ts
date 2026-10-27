// Original short teaching notes. Source links are further reading, not live data.
export const sources = {
  accounts: {
    label: "SEC: reading financial statements",
    url: "https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide",
  },
  fundamentals: {
    label: "Zerodha Varsity: fundamental analysis",
    url: "https://zerodha.com/varsity/module/fundamental-analysis/",
  },
  risk: {
    label: "Investor.gov: allocation and diversification",
    url: "https://www.investor.gov/introduction-investing/getting-started/asset-allocation",
  },
  index: {
    label: "Investor.gov: index funds",
    url: "https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-4",
  },
  factors: {
    label: "MSCI: factor investing",
    url: "https://www.msci.com/research-and-insights/blog-post/what-is-factor-investing",
  },
  rbi: {
    label: "RBI: original policy releases",
    url: "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
  },
  budget: {
    label: "Government of India: Union Budget",
    url: "https://www.indiabudget.gov.in/",
  },
  filings: {
    label: "NSE: company announcements",
    url: "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
  },
} as const;
export type SourceKey = keyof typeof sources;
export type Lesson = {
  id: string;
  title: string;
  minutes: number;
  note: string;
  task: string;
  source: SourceKey;
  question: string;
  options: string[];
  answer: number;
  explanation: string;
};
export const lessons: Lesson[] = [
  {
    id: "business",
    title: "1. Start with the business",
    minutes: 15,
    note: "A stock represents an ownership interest. Before forecasting its price, explain who pays the company, what they buy and why they return. Sketch inputs → operations → customers. A sector name is only a starting label; businesses within it can have different economics.",
    task: "Pick two understandable sectors. Write one measurable demand question for each; favour the one whose customers and evidence you can explain.",
    source: "fundamentals",
    question: "Which is the best starting research question?",
    options: [
      "Which stock will double?",
      "Who buys this product, and what changes their spending?",
      "Which ticker is trending?",
    ],
    answer: 1,
    explanation:
      "Customer economics gives you a testable business question; a desired return or popularity does not.",
  },
  {
    id: "evidence",
    title: "2. Choose companies and collect evidence",
    minutes: 20,
    note: "Compare two or three companies with similar products and geography. Confirm legal names, symbols, dates and reporting basis. Use filings for disclosed facts; label management guidance, outside estimates and your assumptions separately. Missing evidence is a research task.",
    task: "Open the screener, shortlist two peers, then save their original annual-report links and three unanswered questions in a company notebook.",
    source: "filings",
    question: "A news story mentions a project bid. What is established?",
    options: [
      "Revenue is guaranteed",
      "The company has won",
      "A reported bid needs checking against an original disclosure",
    ],
    answer: 2,
    explanation:
      "Bid, award, execution, recognised revenue and collected cash are different stages.",
  },
  {
    id: "statements",
    title: "3. Read the accounts together",
    minutes: 25,
    note: "The balance sheet is a dated snapshot; income and cash-flow statements cover periods. Profit and operating cash can diverge. Read notes and auditor commentary, then compare the same consolidated or standalone basis and units.",
    task: "For two years, record revenue, profit, operating cash, debt and receivables with page references. Explain one change using the notes.",
    source: "accounts",
    question: "Profit rose but receivables grew much faster. What next?",
    options: [
      "Assume fraud",
      "Inspect collection, revenue recognition and cash flow",
      "Ignore it because profit rose",
    ],
    answer: 1,
    explanation:
      "This is a reason to investigate cash conversion, not proof of misconduct.",
  },
  {
    id: "drivers",
    title: "4. Build a demand and supply model",
    minutes: 25,
    note: "Build revenue from operating drivers: units × realised price, or customers × spending. Check capacity, utilisation, competition and substitutes. A growing market does not guarantee company growth. Avoid counting both market share gains and the same volume gains twice.",
    task: "Choose one company; write three drivers, their sources and the evidence that would contradict each. Banks and insurers need specialised models.",
    source: "fundamentals",
    question: "An industry adds substantial capacity. What should you test?",
    options: [
      "Only demand growth",
      "Pricing, utilisation and competitor response",
      "An automatic rise in margins",
    ],
    answer: 1,
    explanation:
      "Supply can grow faster than demand, putting pressure on prices and returns.",
  },
  {
    id: "news",
    title: "5. Turn news into research questions",
    minutes: 20,
    note: "Use event → actual company exposure → operating change → financial effect → timing. Check the original release, effective date and counterarguments. A policy proposal, funding allocation and paid order are different evidence. Good business news can already be reflected in the price.",
    task: "Read one India and one world headline. Record who benefits, who pays, what must happen first and what evidence would prove you wrong.",
    source: "rbi",
    question: "Oil falls. Does every cement company benefit equally?",
    options: [
      "Yes",
      "No; check fuel mix, contracts, freight and selling prices",
      "All share prices must rise",
    ],
    answer: 1,
    explanation:
      "Exposure and pass-through determine the business effect; expectations also affect stock prices.",
  },
  {
    id: "valuation",
    title: "6. Separate a good company from its price",
    minutes: 25,
    note: "Valuation asks what assumptions a price requires. Compare bear, base and bull operating cases. For profitable non-financial firms, a simplified EPS × assumed P/E exercise can reveal sensitivity. Losses, cyclicals, banks and insurers require different treatment.",
    task: "Use the practice lab. Raise profit but lower the assumed multiple; explain how a stronger business can still produce a lower price scenario.",
    source: "fundamentals",
    question: "EPS rises 10%, while P/E falls 20%. What happens to EPS × P/E?",
    options: ["Rises 10%", "Falls 12%", "Stays flat"],
    answer: 1,
    explanation:
      "1.10 × 0.80 = 0.88. A multiple change can outweigh earnings growth.",
  },
  {
    id: "risk",
    title: "7. Think about losses and portfolios",
    minutes: 20,
    note: "Risk includes permanent loss, funding pressure, concentration and being forced to sell. Match investments to horizon and liquidity needs. Diversification reduces some concentration risk, but does not eliminate losses. Several funds can still hold overlapping exposures.",
    task: "List three ways your thesis fails. Check whether your other ideas depend on the same rate, commodity or customer cycle.",
    source: "risk",
    question:
      "Five stocks all depend on the same commodity. Are you broadly diversified?",
    options: [
      "Yes, five tickers are enough",
      "No, their business risks may overlap",
      "Diversification prevents any loss",
    ],
    answer: 1,
    explanation: "Count underlying exposures, not just tickers.",
  },
  {
    id: "strategies",
    title: "8. Compare strategies honestly",
    minutes: 20,
    note: "A strategy needs explicit selection, sizing, entry, exit and review rules. Test costs, liquidity, benchmark choice and unseen periods. A backtest can accidentally use future information or omit failed companies. A convincing historical chart is not a promise.",
    task: "Compare two strategy cards. Write the environment where each could fail, then inspect the assumptions in the backtester before running an example.",
    source: "factors",
    question:
      "A test uses today's index members for ten years of history. What is a concern?",
    options: [
      "Survivorship bias",
      "Guaranteed diversification",
      "No issue if returns look strong",
    ],
    answer: 0,
    explanation:
      "Today's members exclude some firms that failed or left; results can be distorted.",
  },
  {
    id: "pitch",
    title: "9. Write and challenge a stock pitch",
    minutes: 30,
    note: "Present a business, a differentiated thesis, evidence, scenarios, catalysts and failure conditions. Separate fact from interpretation. Show what expectations you disagree with and why. Keep a dated record and compare later results with your original assumptions.",
    task: "Use the pitch worksheet. Ask a club member to argue the opposite case. A watch or insufficient-evidence conclusion is valid.",
    source: "filings",
    question: "Which thesis is most testable?",
    options: [
      "Management is great",
      "The stock looks cheap",
      "Collections improve by next results; track receivable days and CFO",
    ],
    answer: 2,
    explanation:
      "A measurable outcome and review date make it possible to revise a view honestly.",
  },
];

export const terms: { term: string; meaning: string; source: SourceKey }[] = [
  [
    "Revenue",
    "Sales recognised in a period, before expenses; not necessarily cash collected.",
    "accounts",
  ],
  [
    "Net profit / PAT",
    "Earnings after expenses and tax; inspect one-off items.",
    "accounts",
  ],
  [
    "Balance sheet",
    "Assets, liabilities and equity at a specified date.",
    "accounts",
  ],
  [
    "Operating cash flow / CFO",
    "Cash from operations after relevant non-cash and working-capital adjustments.",
    "accounts",
  ],
  [
    "EPS",
    "Profit attributable to ordinary shareholders divided by weighted-average shares; check dilution.",
    "accounts",
  ],
  [
    "P/E",
    "Price per share ÷ EPS. Non-positive EPS makes this comparison unhelpful.",
    "accounts",
  ],
  [
    "Net margin",
    "Net profit ÷ revenue × 100; compare matching periods and basis.",
    "accounts",
  ],
  [
    "Debt",
    "Borrowed obligations; examine interest, maturity and covenants, not only totals.",
    "accounts",
  ],
  [
    "Working capital",
    "Operating funds tied up in items such as inventory and receivables, net of payables.",
    "fundamentals",
  ],
  [
    "Capex",
    "Spending on long-lived assets; distinguish maintenance from expansion.",
    "fundamentals",
  ],
  [
    "Free cash flow",
    "Cash remaining after relevant reinvestment; specify your equity or enterprise definition.",
    "fundamentals",
  ],
  [
    "ROE",
    "Net income ÷ average equity; leverage and unusual equity can distort it.",
    "fundamentals",
  ],
  [
    "ROCE",
    "Return on capital employed; state profit and capital definitions before comparison.",
    "fundamentals",
  ],
  [
    "Enterprise value",
    "Value of operating claims; commonly equity value plus debt less cash, with adjustments.",
    "fundamentals",
  ],
  [
    "Dilution",
    "More shares can reduce each existing share's participation in earnings.",
    "fundamentals",
  ],
  [
    "Consolidated",
    "Accounts including controlled subsidiaries; do not mix with standalone figures.",
    "filings",
  ],
  [
    "YoY / QoQ",
    "Year-on-year versus quarter-on-quarter; seasonality affects interpretation.",
    "filings",
  ],
  [
    "Order book",
    "Unfulfilled orders; cancellation, timing and execution determine eventual revenue.",
    "filings",
  ],
  [
    "Related-party transaction",
    "A transaction with a connected party; inspect terms, approvals and disclosures.",
    "filings",
  ],
  [
    "Catalyst",
    "An event that might change expectations; neither its timing nor impact is assured.",
    "filings",
  ],
  [
    "Inflation",
    "Change in a price index over a stated period; headline and component measures differ.",
    "rbi",
  ],
  [
    "Policy rate",
    "A central-bank instrument influencing funding conditions; transmission varies.",
    "rbi",
  ],
  [
    "Basis point",
    "0.01 percentage point; 100 basis points equal one percentage point.",
    "rbi",
  ],
  [
    "Currency exposure",
    "Net sensitivity to exchange rates after revenues, costs, debt and hedges.",
    "rbi",
  ],
  [
    "Fiscal deficit",
    "Government spending less non-borrowed receipts; inspect the period and definition.",
    "budget",
  ],
  [
    "Allocation vs expenditure",
    "Budgeted money differs from money actually spent or collected by a company.",
    "budget",
  ],
  [
    "Diversification",
    "Spreading underlying exposures; it does not guarantee protection from losses.",
    "risk",
  ],
  [
    "Liquidity",
    "Ability to meet cash needs or trade without a large price impact.",
    "risk",
  ],
  [
    "Index fund",
    "A fund following an index; fees, trading and tracking differences affect returns.",
    "index",
  ],
  [
    "Benchmark",
    "A relevant comparison portfolio; use consistent currency, periods and dividends.",
    "index",
  ],
  [
    "Momentum",
    "A strategy characteristic based on past relative price strength; reversals can hurt.",
    "factors",
  ],
  [
    "Drawdown",
    "Fall from a previous peak; a 50% loss needs a 100% gain to recover.",
    "risk",
  ],
].map(([term, meaning, source]) => ({
  term,
  meaning,
  source: source as SourceKey,
}));

export const strategies = [
  {
    name: "Value",
    idea: "Pay less than a justified estimate of business value.",
    evidence:
      "Normalised earnings, assets, cash generation and valuation scenarios.",
    failure: "A cheap business can deteriorate; a catalyst may never arrive.",
    task: "Explain why a low multiple is deserved or mistaken.",
    source: "factors" as SourceKey,
  },
  {
    name: "Growth",
    idea: "Study durable expansion and reinvestment opportunities.",
    evidence:
      "Customer demand, unit economics, competitive supply and financing.",
    failure:
      "Overpaying or disappointing growth can overwhelm business progress.",
    task: "Separate market growth from company share gains.",
    source: "fundamentals" as SourceKey,
  },
  {
    name: "Quality",
    idea: "Seek resilient profitability and financial strength.",
    evidence:
      "Cash conversion, leverage, repeat demand and capital allocation.",
    failure: "Quality can be overpriced or weaken as competition changes.",
    task: "Challenge one apparently strong metric using the accounts.",
    source: "factors" as SourceKey,
  },
  {
    name: "Momentum",
    idea: "Use explicit rules based on past relative price strength.",
    evidence:
      "Adjusted prices, turnover, liquidity and realistic transaction costs.",
    failure: "Sharp reversals, crowding and trading costs.",
    task: "Specify formation period, rebalancing and exit rules before testing.",
    source: "factors" as SourceKey,
  },
  {
    name: "Broad index investing",
    idea: "Follow a defined broad market index.",
    evidence: "Index coverage, concentration, fees and tracking difference.",
    failure: "Market losses remain; a sector index can be concentrated.",
    task: "Read an index methodology and a fund factsheet.",
    source: "index" as SourceKey,
  },
  {
    name: "Event-driven research",
    idea: "Investigate a specific change such as capacity, a policy or an award.",
    evidence: "Original disclosures, conditions, timing and cash consequences.",
    failure: "The event can fail, be delayed or already be priced in.",
    task: "Track bid → award → execution → collection separately.",
    source: "filings" as SourceKey,
  },
];

export const cases = [
  {
    title: "2007–09: housing and credit crisis",
    happened:
      "US housing and credit stress developed into a severe financial and economic downturn. The Federal Reserve history records a recession from December 2007 to June 2009.",
    mechanism:
      "Research how leverage, funding and weaker customer demand interact. Exposure differs across firms; this episode is not a template for every slowdown.",
    task: "For a cyclical business, find debt maturities, liquidity and evidence of customer demand under stress.",
    url: "https://www.federalreservehistory.org/essays/great-recession-of-200709",
    source: "Federal Reserve History",
  },
  {
    title: "2020: pandemic disruption and policy response",
    happened:
      "Pandemic disruption hit activity and financial markets. On 23 March 2020 the Federal Reserve announced further measures to support credit and market functioning.",
    mechanism:
      "Separate the demand shock, operating restrictions and financing response. A liquid balance sheet and online channels could matter differently for each business.",
    task: "Compare two companies' original 2020 reports. Distinguish temporary disruption from lasting changes in demand.",
    url: "https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323b.htm",
    source: "Federal Reserve, 23 March 2020",
  },
  {
    title: "2022: war, commodities and inflation",
    happened:
      "The IMF's April 2022 outlook described weaker global growth prospects and inflation pressure associated with the war in Ukraine alongside existing stresses.",
    mechanism:
      "Trace input costs, freight, customer affordability and pricing power. Commodity producers and users can have opposite exposures; contracts and hedges change timing.",
    task: "Draw the cost bridge for a cement company. Identify actual fuel mix before assuming an oil-price effect.",
    url: "https://www.imf.org/en/Blogs/Articles/2022/04/19/blog-weo-war-dims-global-economic-outlook-as-inflation-accelerates",
    source: "IMF, April 2022",
  },
  {
    title: "2023: US regional-bank failures",
    happened:
      "The FDIC's discussion of the 2023 failures examines funding, uninsured deposits and interest-rate risk, including the rapid withdrawal of deposits.",
    mechanism:
      "Asset values, deposit concentration and liquidity can interact. Accounting earnings alone do not reveal the ability to meet sudden withdrawals.",
    task: "For a bank, research deposit mix, liquidity and rate sensitivity. Do not apply an industrial company's debt checklist unchanged.",
    url: "https://www.fdic.gov/news/speeches/2024/lessons-learned-us-regional-bank-failures-2023",
    source: "FDIC retrospective, 2024",
  },
];

export const pitchFields = [
  ["identity", "Company, ticker, report date and investment horizon"],
  ["business", "Business, customers and why these peers are comparable"],
  [
    "thesis",
    "Three testable thesis points; distinguish fact, guidance and assumption",
  ],
  [
    "evidence",
    "Source URLs, publication dates, pages, periods and reporting basis",
  ],
  [
    "financials",
    "Revenue, profit, cash conversion, debt and governance questions",
  ],
  [
    "valuation",
    "Bear / base / bull assumptions and what the current price requires",
  ],
  ["catalysts", "Catalysts, project stages, dependencies and review dates"],
  [
    "risks",
    "Strongest counterargument, missing evidence and failure conditions",
  ],
  [
    "review",
    "Conclusion (including watch), next evidence to check and dated forecast review",
  ],
] as const;
