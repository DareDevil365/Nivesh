# Free AI newsletters to subscribe to

Checked against publishers' pages on **15 October 2026**. The runtime reads subscribed issues; it does not automatically subscribe to providers. Signup can be performed separately with the mailbox owner's authorization. Free newsletters can contain sponsorships or links to separate paid products.

| Newsletter | Subscription page | Useful for | Free-tier evidence |
| --- | --- | --- | --- |
| The Rundown AI | [Join for free](https://www.therundown.ai/subscribe) | Practical AI developments, products and workflows | The subscription page explicitly offers free signup; university products are separate. |
| TLDR AI | [Subscribe](https://tldr.tech/ai) | Model releases, developer tools and research | The publisher describes a free weekday newsletter. |
| The Batch | [Subscribe/read](https://www.deeplearning.ai/the-batch/) | Research and industry context | [Free membership includes weekly AI news](https://info.deeplearning.ai/knowledge-base/types-of-memberships). |
| Superhuman AI | [Subscribe for free](https://www.superhuman.ai/) | Tools, practical tutorials and AI news | The homepage says the newsletter is free to read. |
| The Neuron | [Subscribe](https://www.theneuron.ai/newsletter/) | Accessible AI news, tools and explanations | [Publisher newsletter page offers free signup](https://www.theneuron.ai/newsletter/merry-christmas-from-the-neuron/); academy access is separate. |
| Ben's Bites | [Subscribe](https://www.bensbites.com/) | AI products, builders and useful discoveries | [Terms distinguish free and Pro subscriptions](https://catalog.bensbites.com/terms-of-service). Select the free option. |

Start with **The Batch, TLDR AI and The Rundown AI** for a mix of context, technical developments and practical applications. The others add viewpoints but can overlap. Cadence and pricing can change; check the current signup page before accepting an offer.

## Connecting received issues

The reader uses publisher-owned domains from `newsletter_sources.json` and Gmail's reported DMARC result. Website domains do not necessarily equal actual email sending domains. The catalog also includes three exact publisher From identities verified against authenticated signup mail; these retain the correct publisher name and public citation link. No shared-platform domain is approved wholesale. A publisher using a shared platform or a different sending domain may need an explicit exact-address approval after the first issue arrives:

```powershell
python scripts/setup_newsletters.py --approve-sender publisher-address@example.com
python scripts/setup_newsletters.py --check
python scripts/deploy.py configure
```

Use the actual **From address** of the newsletter you subscribed to, not a display name. Do not approve a whole shared platform domain. This command approves that sender for ingestion; it does not subscribe, reply, click confirmation links or change the email. Gmail must report DMARC pass for the issue. Provider/domain coverage is a maintained allowlist, not automatic discovery of every newsletter in your inbox.

The reader searches recent matching senders in Inbox, which includes normal Gmail category tabs. Archived issues are outside this initial adapter. Welcome/confirmation/password emails are excluded. Publisher citations from mailbox issues lead to public publisher pages; private message IDs and personalised tracking URLs are not published.

## Editorial selection and signup verification (15 October 2026)

The core selection is The Batch for research context, TLDR AI for linked technical developments, and The Rundown for accessible applications. Superhuman and The Neuron are supplementary practical perspectives with overlap; Ben's Bites focuses on builders and tools. These roles describe publisher positioning and inspected public pages, not an independent accuracy score or a guarantee about every issue. Subscriber counts and marketing testimonials are not evidence that a claim is true.

Selection criteria are a clear publisher identity, an active public archive or sample, useful topical coverage, a stated free edition, and a manageable contribution beyond duplicate headlines. Commentary, vendor announcements, unreviewed papers and advertised tools need different treatment. Existing source labels preserve those distinctions; automated quote and number checks do not prove editorial accuracy. The current body cleaner removes common advertisement/footer lines but does not reliably detect every sponsored passage. Do not treat sponsored performance claims as independently verified facts.

Authorized browser signup returned explicit success for The Rundown, TLDR AI and The Batch. The Batch's optional courses/events marketing checkbox was deselected. Superhuman's alternative signup returned success after its homepage form failed, and initially requested email confirmation; unrelated partner newsletters were skipped. The Neuron stopped at human verification. Ben's Bites requires explicit acceptance of Substack terms and is pending that confirmation. These are signup-page outcomes, not proof of inbox delivery or successful bot ingestion. No recipient details or credentials are recorded here.

Follow-up verification: TLDR AI and Superhuman email confirmation links returned successful signup/opt-in states. The Neuron passed human verification and sent authenticated welcome mail. Ben's Bites completed its free signup after explicit terms approval and sent an authenticated subscription acknowledgement; optional chat/referral steps were skipped. The Batch showed a successful signup page, but an incoming issue has not yet been observed. Credentials now authenticate locally. Welcome and confirmation messages are operational evidence only and are excluded from news synthesis.
