# Free AI newsletters to subscribe to

Checked against publishers' pages on **15 October 2026**. Subscribe with your chosen newsletter mailbox and confirm any verification email yourself. Subscriptions are not automatically submitted by this project. Free newsletters can contain sponsorships or links to separate paid products.

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

The reader uses publisher-owned domains from `newsletter_sources.json` and Gmail's reported DMARC result. Website domains do not necessarily equal actual email sending domains. A publisher using a shared platform or a different sending domain may need an explicit exact-address approval after the first issue arrives:

```powershell
python scripts/setup_newsletters.py --approve-sender publisher-address@example.com
python scripts/setup_newsletters.py --check
python scripts/deploy.py configure
```

Use the actual **From address** of the newsletter you subscribed to, not a display name. Do not approve a whole shared platform domain. This command approves that sender for ingestion; it does not subscribe, reply, click confirmation links or change the email. Gmail must report DMARC pass for the issue. Provider/domain coverage is a maintained allowlist, not automatic discovery of every newsletter in your inbox.

The reader searches recent matching senders in Inbox, which includes normal Gmail category tabs. Archived issues are outside this initial adapter. Welcome/confirmation/password emails are excluded. Publisher citations from mailbox issues lead to public publisher pages; private message IDs and personalised tracking URLs are not published.
