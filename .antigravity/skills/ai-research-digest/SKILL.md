---
name: ai-research-digest
description: Best practices, closed category vocabulary, triage rules, and document synthesis guidelines for Nivesh's Pseudo-Brain AI Research Digest.
---

# AI Research Digest ("Pseudo-Brain") Guidelines

## Core Principles

1. **NUMBERS NEVER COME FROM THE LLM.**
   - All financial metrics (P/E, revenue, margins, debt, ratios) come strictly from `fundamentals_cache` parsed by Python code.
   - The LLM only ever summarizes qualitative text (corporate announcements, concalls, news).

2. **Rule-Based Triage First:**
   - Run keyword triage on incoming filing titles before any LLM call.
   - Routine notices (board meeting dates, compliance certificates) stop at triage — logged but not synthesized (saves ~80% of LLM calls).

3. **Closed Vocabulary:**
   - Category Tags: `Financial Results`, `Board Meeting`, `Credit Rating`, `Auditor Resignation`, `Related Party Transaction`, `Litigation & Regulatory`, `Pledge Change`, `Key Personnel Change`, `General Corporate`.
   - Management Tone Flags: `Confident`, `Cautious`, `Mixed`.

4. **Direct Lineage & Source Linking:**
   - Every AI-generated summary line carries an explicit `"AI-summarized from [source]"` tag linking directly to the original filing/transcript URL.

5. **Caching & Quota Shielding:**
   - Summaries are cached permanently by document hash (`raw_text_hash`).
   - Re-visiting a company page costs 0 LLM calls.
