# Reading, research and finance learning release

Prepared and implemented 14 October 2026. This is the preparation plan and delivery record for the personal reading/learning features, not a claim that every possible research feature is complete.

## Research and product choices

The user needs both a daily habit and a route to a defensible college stock pitch. A feed alone does not teach company analysis; an encyclopedia alone does not connect learning to events. The implemented release connects a reading desk, short lessons, source reading, exercises and a saved pitch draft.

Primary educational references checked for this release:

- [SEC financial-statement guide](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide): read related statements and notes, distinguish periods from snapshots and profit from cash.
- [Zerodha Varsity fundamental analysis](https://zerodha.com/varsity/module/fundamental-analysis/): accessible Indian-market further reading for business, accounts and valuation. It is brokerage educational material, not a regulator endorsement or a source of recommendations in Nivesh.
- [Investor.gov asset allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation): horizon, risk and underlying diversification.
- [Investor.gov index funds](https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-4): index implementation, costs and tracking differences.
- [MSCI factor investing](https://www.msci.com/research-and-insights/blog-post/what-is-factor-investing): systematic styles such as value, quality and momentum. MSCI is an index provider; no historical premium or future return is promised here.
- [Federal Reserve History, 2007–09](https://www.federalreservehistory.org/essays/great-recession-of-200709), [Federal Reserve, March 2020](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323b.htm), [IMF, April 2022](https://www.imf.org/en/Blogs/Articles/2022/04/19/blog-weo-war-dims-global-economic-outlook-as-inflation-accelerates) and [FDIC retrospective](https://www.fdic.gov/news/speeches/2024/lessons-learned-us-regional-bank-failures-2023): original institutional records for four selected historical cases. Each case separates historical record from an original research exercise.

The project's analyst protocol supplies the workflow: establish issuer identity, gather evidence, model actual exposures, test contrary cases and separate business outcomes from stock-price assumptions. Lessons and definitions are original concise teaching notes with further-reading links, not copied course material. US educational references teach concepts; they do not establish Indian reporting or regulatory requirements. Company conclusions still require current Indian issuer and regulator evidence.

## Delivery sequence and completed scope

1. **Free discovery.** Add six global/US/India/policy/commodity/world-event RSS searches, company-name news and a custom topic search. Preserve source and publication date, drop invalid dates/links and expose outages. Fetches occur on demand, with caching and bounded concurrency; no scheduler was activated.
2. **Reading workflow.** Suggest one story per lens when available; filter stock-pick and off-topic headlines. Label the ranking as a heuristic. Add publisher links, seven introductory news terms, save/read markers and JSON export. Saved stories can be opened even when the API fails.
3. **Community separation.** Add Reddit previews and X search access in a distinct company panel. Reddit currently covers one public community and can be unavailable. X is explicitly search-link-only; no posts, login credentials or sentiment are fetched. Neither source changes company financials, pending projects or supply-chain edges.
4. **Learning path.** Add nine ordered lessons with practical tasks, multiple-choice checks, explanations and browser-local progress. Cover sector/company choice, evidence, statements, drivers, news transmission, valuation, risks, strategies and the pitch.
5. **Reference and comparison.** Add 32 searchable finance terms, four historical cases and six strategy cards with evidence requirements, failure conditions and exercises. Link to the existing backtester without pretending it implements fundamental strategies automatically.
6. **Practice and output.** Add deterministic revenue/profit/dilution/EPS/P-E arithmetic and a nine-field stock-pitch worksheet with local saving and combined progress/draft export. An illustrative loss-making business receives no P/E-based price. Editing assumptions clears the previous result.
7. **Validation and documentation.** Run the offline backend suite, production frontend build, live free-feed checks and browser interaction/error/mobile tests. Record actual checks in `VALIDATION.md` and architecture/limitations in `PROJECT_GUIDE.md`.

## Why these mechanisms

RSS avoids adding credentials or AI costs for basic reading. The Google News RSS endpoint is unofficial and has no guaranteed coverage or availability; Reddit also controls access. A paid news API could later supply a contractual feed, but would not solve relevance or verification on its own. Publisher articles remain on their sites, including any access requirements. No paywalls or login protections are bypassed.

Deterministic code handles parsing, date windows, deduplication and arithmetic. Static, reviewed teaching content avoids variable generated definitions and repeated token expense. An AI-generated daily interpretation was deliberately not added: headline-only input cannot support reliable financial conclusions. Existing explicit AI research still uses its separate evidence pipeline and existing Gemini configuration.

The learning frontend uses existing React/Next and localStorage rather than new accounts or a database migration. This fits single-person practice but has no cross-device sync, multi-draft management or multi-tab merge guarantees. Export copies before clearing browser storage. The scenario API uses existing FastAPI/Pydantic validation rather than duplicating financial arithmetic in UI event handlers. It is self-contained and does not call market-data or AI services.

## Failure cases and acceptance

| Case | Implemented handling / validation |
| --- | --- |
| Feed returns HTML, XML entities, oversized body, timeout or error | Reject and expose unavailable state; retain labelled stale cache where available |
| Provider failure versus quiet company | Distinct unavailable/no-matches states; no claim that nothing happened |
| Wrong company name, future date, unsafe link or duplicate | Text matching/date/link/dedup guards; matching remains unverified issuer scope |
| Stock tips or unrelated article from a familiar publisher | Excluded from Start here using headline-form and category-relevance checks |
| Search phrase interpreted as query operators | Topic normalisation and literal quoted search; validation for empty/punctuation input |
| Refresh spam or concurrent callers | Cache cooldown, single-flight query guard and four feed slots |
| Browser storage missing/corrupt or write rejected | Session use and export; learning data read failure leaves the previous stored copy untouched |
| Quiz skipped/wrong/correct/repeated | Feedback; only correct checks add completion, without duplicate counts |
| Margin zero/negative, total revenue loss | No P/E scenario price; explicitly not applicable |
| Zero/tiny shares, nonfinite or excessive inputs, wrong fields | Pydantic rejects before arithmetic; extreme accepted values checked finite |
| Dilution, earnings growth with multiple compression | Independently calculated examples and browser checks |
| Assumption edited after calculating | Previous result cleared immediately |
| Backend unavailable | Teaching content/worksheet still work locally; saved reading list has an independent entry point; calculator shows error |
| Narrow mobile viewport | Browser width and visual screenshot inspection |

## Limits and possible later work

This release is a learning and discovery tool, not exhaustive real-time surveillance, a fully scraped newspaper archive or an automated stock recommendation. Headlines are not read article bodies. Ranking does not establish importance, independent corroboration or event materiality. Repetition across publishers may be syndicated. Heuristics can miss stories and misclassify opinion.

Not implemented: economic-calendar surprise data, licensed X aggregation, comprehensive Reddit comments, source-family claim/denial chains, push notifications, automatic policy-to-company financial impact, a historical price-event attribution database, automatic pitch grading or all-sector accounting models. These need suitable datasets, access, methodology and separate acceptance tests. The user's earlier AI efficiency plan remains a broader roadmap; this release does not claim to solve semantic accuracy of its live AI reports.
