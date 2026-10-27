# Company and sector monitoring: feature and implementation specification

Prepared 14 October 2026. **First increment implemented; broader monitoring remains proposed.** This extends [AI_RESEARCH_IMPLEMENTATION_PLAN.md](AI_RESEARCH_IMPLEMENTATION_PLAN.md). The app now provides a bounded disclosure timeline, possible follow-up passages and a private project ledger. Comprehensive news/rumour feeds, automatic tender matching and scheduled alerts remain unconnected.

## 1. Product goal

Help a researcher answer: **What changed, what is still pending, why might it matter, and what evidence should I check next?**

Use one evidence-linked event timeline rather than separate disconnected news summaries. Preserve direct company developments, sector developments, supplier/customer exposures, financial reports, management statements and uncertain reports as different kinds of evidence. A positive headline does not by itself imply higher earnings or a higher stock price.

## 2. Features to add

| Feature | What the researcher sees | Important constraint |
| --- | --- | --- |
| Company developments | Results, disclosures, orders, launches, plant changes, financing, litigation and material operating events | Source, publication/effective date and issuer scope accompany each item |
| Pending projects and catalysts | Bids, applications, approvals, acquisitions, product qualifications and commercial milestones awaiting an outcome | Track exact stage; pending is not won, approved or revenue-producing |
| Rumour and clarification ledger | Original report, source chain, what is claimed, company/regulator response and later corrections | Rumours stay unverified; repetition does not increase factual status |
| Reports and results hub | Annual/quarterly reports, presentations, transcripts, auditor notes and selected comparable changes | Preserve period, basis, units, restatements and unreviewed-extraction status |
| Management and governance timeline | CEO/CFO/auditor changes, strategy statements, capital allocation, resignations and disclosed reasons | Record position and tenure; a resignation alone does not establish misconduct |
| Sector and policy context | Relevant rules, demand indicators, input costs, rival capacity and customer-sector developments | Connect actual geography/product exposure; sector membership alone is insufficient |
| Upcoming-event calendar | Announced results meetings, AGMs, votes, bid deadlines, hearings and management-guided milestones | Confirmed dates, estimated windows and unknown dates have separate labels |
| What changed since my last review? | New disclosures, corrected figures, status transitions, guidance versus actuals and thesis implications | Reuse source versions; do not merely regenerate a different summary |
| Research checklist and thesis links | Questions raised by each development, supporting/contradicting evidence and next observable milestone | A model can propose implications, not certify a thesis |
| Optional watchlist digest | Material changes for followed companies/sectors and pending items whose sourced dates passed | Opt-in, deduplicated, quiet when unchanged; show collection freshness |

Start with manual refresh and an in-app review inbox. Scheduled checks and external delivery are later product features with explicit opt-in; this specification does not create any automation or send notifications.

## 3. Pending projects need separate lifecycles

Do not force every opportunity through one “project progress” percentage.

| Project type | Illustrative milestones; only sourced stages may be populated |
| --- | --- |
| Tender/order | Opportunity published → issuer participation disclosed → bid submitted → technical qualification → financial evaluation → preferred/L1 status → award/letter of acceptance → contract → execution → recognized revenue → collection |
| Owned plant/expansion | Announced plan → land/funding/required permissions → construction → commissioning/trial run → commercial production → utilization → sales/cash generation |
| Regulatory application/product qualification | Application → acceptance for review → questions/testing → decision/conditions → launch or permitted operation → actual commercial adoption |
| Acquisition | Proposal → agreement → required approvals/conditions → closing → integration; withdrawal, rejection and revised terms are separate branches |
| Policy benefit | Proposal → notified rule → issuer/product eligibility → application → allocation/approval → implementation → claimed/received benefit |

Actual processes differ: stages can occur in parallel, be skipped, be revised or reverse. Tender portals may publish an opportunity or opening date without publicly identifying every bidder. **Never infer that a company applied because a suitable tender exists.** No result found means “no later outcome found within the checked sources,” not “lost,” “cancelled,” or “still pending with certainty.”

For a bid, retain tender/application ID, procuring authority, location, product/scope, issuer or consortium member, disclosed participation basis, full project value versus issuer share, currency, duration, status dates, source and next confirmation needed. A preferred bidder or L1 position is not automatically a final award. Contract value is not annual revenue, profit or cash; consortium shares, conditions and execution periods matter.

For each item distinguish **current evidenced stage**, **management's stated next step**, **officially scheduled decision date**, **researcher's estimated window**, **last checked time**, and **data availability**. An estimated window passing creates a review question. Only an attributable source can establish a changed official deadline, delay, withdrawal, award or rejection.

## 4. Rumours, news and management claims

Store the statement separately from its evidence status:

- **Official document available:** the filing exists; its contents can still be management assertions or forward guidance.
- **Reported by a named publication:** retain attribution, original article/date and primary-source links when available.
- **Unverified rumour:** no adequate confirmation; place in a separate lane, excluded from confirmed facts and financial baselines.
- **Company response/denial:** record exactly what was denied or clarified and when; do not turn the response into a broader verified conclusion.
- **Independent confirmation, official finding, correction or retraction:** link the original claim and retain the audit trail, including partial confirmations.

Track the original origin where discoverable. Ten syndicated stories or reposts of one source count as one source family. Distinguish new developments from recycled old headlines. A source's credibility, evidence availability and business relevance are separate attributes, not one opaque confidence percentage.

A rumour cannot create a confirmed supplier/customer edge, overwrite an earnings input, or become the base case of a valuation. It can create a clearly labelled diligence question or an explicit user-owned scenario assumption. Avoid a social-media firehose in the first release; a manually submitted public link plus source checking is a safer, cheaper starting scope. Unsupported allegations and sensational summaries are not repeated as facts.

News sentiment is optional background metadata at most. Prioritize what changed, the causal mechanism, contrary evidence and timing. Do not translate “positive/negative news” into an automatic buy/sell signal or a guaranteed price reaction.

## 5. Example: a cement company

This is a generic research template, not a current sector forecast or a claim about a named company.

| Development | Company exposure to establish | What to inspect next |
| --- | --- | --- |
| Infrastructure/housing spending announcement | Geographic sales, customer/channel mix and relevant demand history | Allocation versus actual expenditure, project execution and cement dispatches |
| Coal/petcoke, electricity or freight change | Fuel mix, procurement contracts, power sourcing, plant location and transport routes | Timing of pass-through, inventory, hedges, energy efficiency and regional selling prices |
| Competitor announces a plant | Overlapping sales region, product, logistics and realistic commissioning schedule | Regional supply/demand, utilization, pricing and the competitor's approvals/funding |
| Mining/environmental approval or restriction | Specific site, limestone supply, capacity and legal entity | Conditions, remaining permissions and actual operating status |
| CEO discusses expansion/pricing | Full dated statement, existing commitments and later company disclosures | Financing, milestones, guidance versus actuals and contrary operating evidence |
| Acquisition or industry consolidation | Parties, assets/regions, transaction terms and applicable approvals | Conditions, closing, integration costs, leverage and competitive response |

Operating metrics may include sales volume, realization, utilization, cost/tonne, operating margin, energy/freight exposure, working capital and capex, when disclosed. Preserve product definitions and regional differences. Bag/tonne conversions require stated weight; accounting/tax definitions and currencies remain explicit. Do not assume a national price or policy has the same effect on every plant.

The explanation follows: **event → evidenced exposure → operating effect → financial effect → timing → competing explanation**. Missing links remain unanswered questions.

## 6. Sources and collection limits

| Need | Starting sources | Integration status |
| --- | --- | --- |
| Company news, reports and clarifications | Issuer IR and [NSE corporate announcements](https://www.nseindia.com/companies-listing/corporate-filings-announcements), plus reviewed BSE adapters | Existing bounded issuer discovery can be extended; no comprehensive news coverage claim |
| Public tender opportunity, dates and available outcome records | [Government eProcurement portal](https://eprocure.gov.in/eprocure/app), relevant authority/state/PSU portals and issuer disclosures | New reviewed adapters required; public participation/outcome visibility varies |
| Environmental proposal/permission | [PARIVESH](https://parivesh.nic.in/) and the relevant authority's original records | Candidate source; direct page retrieval timed out during planning, so programmatic access is unverified |
| Merger notices/decisions | CCI [notices under review](https://cci.gov.in/public/combination/notice-under-review) and [Section 31 orders](https://cci.gov.in/public/combination/orders-section31) | CCI navigation was inspected; direct list retrieval timed out, adapter access remains unverified |
| Policy, economic and sector drivers | Responsible ministry/regulator, PIB, RBI, MoSPI and original notified rules | PIB/RBI leads already exist; broad sector time-series and policy tracking require new adapters |
| Independent reporting and rumour discovery | Licensed news/search feeds and reputable original reporting | Not connected; evaluate coverage, provenance, permitted usage and price before choosing a provider |

Portal existence is not an API contract. Search results do not prove automated access, completeness or a current project outcome. Do not scrape around login/CAPTCHA/paywall restrictions. Start with manual official links and current supported feeds, then validate adapters one at a time. News links/snippets and permitted summaries are sufficient where article republication is not licensed.

## 7. Proposed event data and processing

Add records for `event`, `event_observation`, `pending_item`, `event_entity_link`, `claim_response` and optional `watch_rule`. Each observation stores issuer/entity IDs, event/project IDs, source/evidence references, source family, publication/effective dates and timezone, observed stage, claim status, sector/product/geography tags, last-check time and supersession/correction links.

Store immutable observations; calculate the current displayed state from a versioned reducer that preserves unresolved contradictions. Resolve events using authority/tender IDs, legal entity, location and scope where possible. Similar titles or names alone cannot merge projects. A follow-up may be another phase, lot or consortium member rather than the original project's outcome.

Processing flow:

1. Fetch bounded metadata for explicitly selected issuers/sectors and supported sources.
2. Detect new/changed items with IDs and hashes; separate “newly found” from “newly published.”
3. Deduplicate syndication and issuer/exchange copies; retrieve original permitted evidence.
4. Extract candidate event types/entities/dates using scripts, then AI only for ambiguous classification or selected explanation.
5. Validate identity, timeline, state transitions and claim origin. Quarantine ambiguous matches for review.
6. Update the event timeline and pending-item view. Explain changed status with old/new supporting evidence.
7. Retrieve verified business exposures and relevant financial facts; AI can propose conditional implications with evidence IDs.
8. Update affected thesis/scenario sections and an optional opted-in digest. Do not rerun a full company report for every headline.

Use the main plan's snapshot, job, cache, owner isolation, retry and aggregate-budget contracts. Monitoring hashes/metadata do not require AI calls. Reserve AI for material new evidence or explicit user questions; reuse one interpreted sector event across companies while checking each company's distinct exposure. Never propagate company impact solely through an unverified supply-chain link.

Scheduled local monitoring runs only while the backend/scheduler is running. Hosted continuous monitoring needs an explicitly deployed scheduler, persisted cursors/leases and source budgets. Show feed freshness and outages; a quiet feed is not proof that nothing happened. Cadence is configurable by source/event urgency and provider conditions, with bounded catch-up and no endless minute-by-minute polling.

## 8. Interface and acceptance criteria

Proposed company workspace areas: **Developments**, **Pending projects**, **Reports**, **Management**, **Sector context**, and **My thesis**. Keep the existing financial, supply-chain and notebook workflows; avoid adding six top-level tabs if filters and a unified timeline work better.

Each event card answers:

- What was reported, by whom, and when?
- Is this an official observation, management claim, independent report or rumour?
- What changed from the previous evidenced status?
- Why might it matter to this company, and which exposure is still unknown?
- What is the next dated milestone or confirmation to look for?
- Which source opens the original evidence, and when was it last checked?

Acceptance tests include: undisclosed bid participation, L1 versus award, award versus revenue, consortium share, stale pending status, revised/cancelled tender, same-name project, approval with conditions, official-date versus estimated-window expiry, CEO versus sector-peer quotation, management change without inferred motive, recycled/translated/syndicated rumours, partial denial, later correction, changed source content, irrelevant sector policy, unsupported supplier propagation, duplicated digest, source outage and cancelled local monitoring. UI and exports must preserve all distinctions.

No outcome probabilities, materiality ratios or sentiment-derived forecasts appear without explicit methodology and suitable data. For example, a project-value/revenue ratio cannot be computed until the issuer share, currency, period and revenue definition are compatible. Impact priority can use transparent labels such as “earnings-related, unquantified” instead of a fabricated score.

## 9. Delivery order and dependencies

| Increment | Deliverable | Dependency / done condition |
| --- | --- | --- |
| M1 | Dated developments/report timeline with evidence and “since last review” | Main P1/P2 provenance and retrieval; no AI required for basic events |
| M2 | Pending-item ledger and manual project/source linking | Versioned observations and source-backed stage transitions; ambiguous matching tests pass |
| M3 | Management, rumour/response lanes and targeted sector context | Source-family deduplication, claim-origin labels and exposure checks |
| M4 | Financial/report changes, guidance-versus-actual review and thesis links | Main P3/P6 accepted outputs, compatible financial facts and driver models |
| M5 | Opt-in scheduled digests and reviewed external adapters | Main P4 jobs/budgets, source-access validation and freshness/cancellation tests |

Prioritize M1 and M2: they directly address “the company applied, but the result is not out.” Start with filings and manually linked official records rather than paying for a broad news feed before its incremental value is measured. These are planned features; no new monitoring service, paid subscription or alerts were activated while writing this specification.


## Implemented increment: 14 October 2026

Research workflow → Developments & pending projects now provides a searchable/category-filtered disclosure timeline, source excerpts versus unread headlines, up to four additional short event attachments, and potential follow-up passages. The private ledger supports tender, expansion, approval, acquisition and general project records with sources, quotes, labelled expected dates and versioned observation history. Updates reject stale versions; passed expected dates cause review flags without changing project stages. JSON export and owner-scoped deletion are available. Entries are researcher-supplied and unverified, and are not sent to AI.

This is an initial M1/M2 implementation using existing retained passages and SQLite. Full-page FTS retrieval, persistent AI jobs, evidence-ID generation, cross-document project matching, guidance-versus-actual analysis, full rumour/denial chains and digests remain proposed. No paid subscription or scheduled alerts have been activated. See [../VALIDATION.md](../VALIDATION.md) and the project guide for tests and limitations. Earlier future-tense descriptions in this specification describe the broader target, not a claim that all features are complete.


## Reading/community increment: 14 October 2026

On-demand company news and one-community Reddit RSS discovery are now connected, with explicit dates, source/failure labels and saved/read markers. X is search-link-only. A global reading desk and a finance learning hub are implemented; see [FINANCE_LEARNING_IMPLEMENTATION_PLAN.md](FINANCE_LEARNING_IMPLEMENTATION_PLAN.md). This does not implement the proposed claim/denial chains, automatic project outcomes, cross-source corroboration, digests or scheduling.
