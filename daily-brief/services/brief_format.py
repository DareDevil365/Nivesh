"""A bounded five-minute news view; full research stays in the email edition."""

import html
import os
import re

from services import news_reader


def enabled():
    return os.getenv("NEWS_BRIEF_MODE", "full").lower() == "short"


def sentence(text, limit, fallback):
    text = " ".join(text.split())
    if len(text.split()) <= limit:
        return text
    chunks = re.split(r"(?<=[.!?])\s+", text)
    first = chunks[0]
    return first if len(first.split()) <= limit else fallback


def select(digest, categories):
    picked = []
    seen = set()
    for section in digest["sections"]:
        if section["id"] not in categories:
            continue
        for bullet in section["bullets"]:
            key = news_reader.headline_fingerprint(bullet["text"])
            if key in seen:
                continue
            seen.add(key)
            picked.append(bullet)
            if len(picked) == 2:
                return picked
    return picked


def news_blocks(bullets):
    blocks = []
    for bullet in bullets[:2]:
        sources = bullet["sources"]
        fallback = (
            "Reported: " + sources[0]["title"]
            if sources
            else "Read the original report for details."
        )
        text = sentence(
            bullet["text"], 35, sentence(fallback, 35, "A source report is linked below.")
        )
        why = sentence(
            bullet["why_it_matters"],
            12,
            "Read the full report for context and remaining uncertainty.",
        )
        links = []
        for source in sources[:3]:
            url = news_reader.safe_link(source["url"])
            if not url:
                raise ValueError("Unsafe brief citation")
            links.append(
                '<a href="'
                + html.escape(url, quote=True)
                + '">'
                + html.escape(source["publisher"])
                + "</a>"
            )
        blocks.append(
            html.escape(text)
            + "\n<i>"
            + html.escape(why)
            + "</i>\n"
            + " · ".join(dict.fromkeys(links))
        )
    return blocks


def sources_in(digest, categories):
    return [source for bullet in select(digest, categories) for source in bullet["sources"]]


def ai_bullets(digest):
    by_id = {i["id"]: i for i in [*digest["items"], *digest.get("research_items", [])]}
    if digest.get("section"):
        return [
            {
                "text": b["text"],
                "why_it_matters": b["why_it_matters"],
                "sources": [by_id[x["source_id"]] for x in b["support"]],
            }
            for b in digest["section"]["bullets"][:2]
        ]
    return [
        {
            "text": "Reported: " + i["title"],
            "why_it_matters": "Source excerpt only; no validated AI interpretation.",
            "sources": [i],
        }
        for i in digest["items"][:2]
    ]
