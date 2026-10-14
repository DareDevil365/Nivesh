"""Source pack and validated email rendering for the scheduled reading assistant.

The Codex heartbeat reads this pack and writes the summary. This service never
reads mailbox contents, sends email or invokes a language model by itself.
"""

import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field

from services import news_reader
from services.filing_sources import fetch_public
from services.local_store import DATA_DIR

IST = timezone(timedelta(hours=5, minutes=30))
DIRECT_FEEDS = (
    ("BBC News Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "world"),
    ("BBC News World", "https://feeds.bbci.co.uk/news/world/rss.xml", "events"),
    ("The Guardian Business", "https://www.theguardian.com/business/rss", "world"),
)
DIRECT_DOMAINS = ("bbc.com", "bbc.co.uk", "theguardian.com")
DIGEST_DIR = DATA_DIR / "news-digests"


def local_day(now=None):
    return (now or datetime.now(timezone.utc)).astimezone(IST).date().isoformat()


def direct_feed(name, url, category):
    try:
        raw = news_reader._fetch(url)
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("Unsupported XML declarations")
        root = ET.fromstring(raw)
        if root.tag != "rss":
            raise ValueError("Not RSS")
        items = []
        for node in root.findall("./channel/item")[:40]:
            link = news_reader.safe_link(node.findtext("link"))
            date = news_reader.parse_date(node.findtext("pubDate"))
            title = news_reader.clean_text(node.findtext("title"), 350)
            if not link or not date or not title:
                continue
            items.append(
                {
                    "id": hashlib.sha256((link + title).encode()).hexdigest()[:24],
                    "title": title,
                    "url": link,
                    "publisher": name,
                    "published_at": date.isoformat(),
                    "category": category,
                    "evidence_text": news_reader.clean_text(node.findtext("description"), 1200),
                    "read_status": "publisher_feed_excerpt",
                }
            )
        return {"id": name, "status": "available" if items else "no_matches", "items": items}
    except (httpx.HTTPError, ET.ParseError, ValueError):
        return {"id": name, "status": "unavailable", "items": []}


def article_text(raw, title):
    soup = BeautifulSoup(raw, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        if re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', script.get_text(), re.I):
            raise ValueError("Publisher marks content as restricted")
    heading = soup.find("h1")
    tokens = set(re.findall(r"[a-z]{4,}", title.casefold())) - {
        "with",
        "from",
        "that",
        "this",
        "after",
        "before",
    }
    if (
        not heading
        or len(tokens & set(re.findall(r"[a-z]{4,}", heading.get_text().casefold())))
        < min(2, len(tokens))
        or not tokens
    ):
        raise ValueError("Article heading does not match feed")
    article = soup.find("article")
    if not article:
        raise ValueError("No article container")
    for node in article.select("script,style,nav,aside,footer,form,button,header"):
        node.decompose()
    paragraphs = [p.get_text(" ", strip=True) for p in article.find_all("p")]
    text = " ".join(paragraphs)
    if len(text) < 600 or re.search(
        r"verify you are human|enable javascript|subscribe to continue|sign in to continue",
        text,
        re.I,
    ):
        raise ValueError("Article unavailable or too short")
    return " ".join(text.split())[:6000]


def enrich(item):
    try:
        host = urlsplit(item["url"]).hostname or ""
        if not any(host == domain or host.endswith("." + domain) for domain in DIRECT_DOMAINS):
            return item
        raw, final, content_type = fetch_public(item["url"], "", 1_500_000, DIRECT_DOMAINS)
        if "html" not in content_type:
            raise ValueError("Not an HTML article")
        return {
            **item,
            "evidence_text": article_text(raw, item["title"]),
            "read_status": "article_excerpt",
            "article_url": final,
        }
    except (httpx.HTTPError, ValueError):
        return {
            **item,
            "article_read_error": "Public article could not be read; retained feed evidence only.",
        }


def collect(now=None, read_articles=True):
    now = now or datetime.now(timezone.utc)
    desk = news_reader.reading_desk(refresh=True)
    feeds = [
        {
            "id": section["id"],
            "status": section["status"],
            "stale": section.get("stale", False),
            "fetched_at": section.get("fetched_at"),
            "items": [
                {
                    **item,
                    "category": section["id"],
                    "evidence_text": "",
                    "read_status": "headline_only",
                }
                for item in section["items"]
            ],
        }
        for section in desk["sections"]
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        feeds.extend(pool.map(lambda entry: direct_feed(*entry), DIRECT_FEEDS))
    records = {}
    for feed in feeds:
        for item in feed["items"]:
            date = news_reader.parse_date(item["published_at"])
            if not date or date < now - timedelta(hours=24) or date > now + timedelta(minutes=5):
                continue
            identity = re.sub(r"\W+", "", item["title"].casefold())
            if identity in records:
                prior = records[identity]
                categories = sorted(set(prior["categories"] + [item["category"]]))
                if item.get("evidence_text") and not prior.get("evidence_text"):
                    records[identity] = {**item, "categories": categories}
                else:
                    prior["categories"] = categories
            else:
                records[identity] = {**item, "categories": [item["category"]]}
    items = sorted(records.values(), key=lambda item: item["published_at"], reverse=True)[:360]
    if read_articles:
        candidates = [
            item
            for item in items
            if any(
                (urlsplit(item["url"]).hostname or "").endswith(domain) for domain in DIRECT_DOMAINS
            )
        ][:12]
        with ThreadPoolExecutor(max_workers=3) as pool:
            replacements = {item["id"]: item for item in pool.map(enrich, candidates)}
        items = [replacements.get(item["id"], item) for item in items]
    return {
        "version": 1,
        "date_ist": local_day(now),
        "generated_at": now.isoformat(),
        "window_hours": 24,
        "feeds": [{k: v for k, v in feed.items() if k != "items"} for feed in feeds],
        "items": items,
        "coverage": {
            "headlines": len(items),
            "article_excerpts": sum(item["read_status"] == "article_excerpt" for item in items),
            "feed_excerpts": sum(item["read_status"] == "publisher_feed_excerpt" for item in items),
            "headline_only": sum(item["read_status"] == "headline_only" for item in items),
        },
        "limitations": "A bounded 24-hour discovery window, not all world news. All retained headlines are supplied to the assistant; at most 12 accessible BBC/Guardian articles are attempted and excerpts truncated to 6000 characters. Google News wrapper links are not bypassed. Feed excerpts and headlines are not full articles. Duplicate titles are merged, but syndication and semantic duplicates may remain. Sources may be delayed, unavailable, restricted or wrong. No price predictions or certified impact analysis.",
    }


class Support(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(min_length=1, max_length=80)
    quote: str = Field(min_length=12, max_length=400)


class Bullet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=15, max_length=650)
    why_it_matters: str = Field(min_length=10, max_length=400)
    support: list[Support] = Field(min_length=1, max_length=3)


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str
    bullets: list[Bullet] = Field(min_length=1, max_length=3)


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[Section] = Field(min_length=1, max_length=6)
    reviewed_ids: list[str] = Field(max_length=360)


def validate_summary(pack, raw):
    summary = Summary.model_validate(raw)
    sources = {item["id"]: item for item in pack["items"]}
    if set(summary.reviewed_ids) != set(sources) or len(summary.reviewed_ids) != len(sources):
        raise ValueError("Summary must acknowledge every retained source ID exactly once.")
    seen = set()
    sections = []
    for section in summary.sections:
        if section.category not in news_reader.CATEGORIES or section.category in seen:
            raise ValueError("Unknown or repeated category")
        seen.add(section.category)
        bullets = []
        for bullet in section.bullets:
            citations, evidence = [], []
            for support in bullet.support:
                source = sources.get(support.source_id)
                if not source:
                    raise ValueError("Unknown source ID")
                text = source["title"] + " " + source.get("evidence_text", "")
                if (
                    " ".join(support.quote.split()).casefold()
                    not in " ".join(text.split()).casefold()
                ):
                    raise ValueError("Supporting quote does not match the collected evidence")
                evidence.append(support.quote)
                citations.append(
                    {
                        key: source[key]
                        for key in (
                            "id",
                            "title",
                            "url",
                            "publisher",
                            "published_at",
                            "read_status",
                        )
                    }
                )
            if not any(
                section.category in sources[entry.source_id]["categories"]
                for entry in bullet.support
            ):
                raise ValueError("Section has no source from its stated category")
            numbers = set(re.findall(r"\d+(?:[.,]\d+)*", bullet.text + " " + bullet.why_it_matters))
            if not numbers.issubset(set(re.findall(r"\d+(?:[.,]\d+)*", " ".join(evidence)))):
                raise ValueError("Summary introduces a number absent from its sources")
            bullets.append(
                {"text": bullet.text, "why_it_matters": bullet.why_it_matters, "sources": citations}
            )
        sections.append(
            {
                "id": section.category,
                "label": news_reader.CATEGORIES[section.category]["label"],
                "bullets": bullets,
            }
        )
    return {
        "version": 1,
        "date_ist": pack["date_ist"],
        "generated_at": pack["generated_at"],
        "subject": "Nivesh morning brief — " + pack["date_ist"],
        "sections": sections,
        "coverage": pack["coverage"],
        "feeds": pack["feeds"],
        "glossary": news_reader.GLOSSARY[:2],
        "limitations": pack["limitations"]
        + " AI paraphrases and interpretations are not semantically certified. Source-ID, quote and numerical checks reject some errors, not all. Why it matters is conditional interpretation, not a recommendation.",
    }


def email_text(digest):
    """Plain-text mail is the delivery format confirmed by the user."""
    coverage = digest["coverage"]
    parts = [
        digest["subject"],
        f"Prepared: {digest['generated_at']}. News window: last 24 hours.",
        f"Coverage: {coverage['headlines']} unique headlines considered; "
        f"{coverage['article_excerpts']} article excerpts, {coverage['feed_excerpts']} publisher feed excerpts, "
        f"{coverage['headline_only']} headline-only items.",
    ]
    for section in digest["sections"]:
        parts.append(section["label"].upper())
        mode = digest.get("summary_modes", {}).get(section["id"])
        if mode:
            parts.append(
                "Summary mode: "
                + mode.replace("_", " ")
                + ". AI interpretation is unverified; fallback is reported headlines only."
            )
        for bullet in section["bullets"]:
            parts.append(bullet["text"])
            parts.append("Why it may matter: " + bullet["why_it_matters"])
            for source in bullet["sources"]:
                url = news_reader.safe_link(source["url"])
                if not url:
                    raise ValueError("Unsafe citation URL")
                parts.append(
                    f"Source: {source['publisher']} - {source['title']}\n"
                    f"Published: {source['published_at']} | {source['read_status'].replace('_', ' ')}\n{url}"
                )
    parts.append("FINANCE TERMS TO LEARN")
    parts.extend(f"{term['term']}: {term['meaning']}" for term in digest["glossary"])
    parts.append("SOURCE COVERAGE AND LIMITATIONS")
    parts.extend(
        f"{feed['id']}: {feed['status']}" + (" (stale)" if feed.get("stale") else "")
        for feed in digest["feeds"]
    )
    parts.append(digest["limitations"])
    return "\n\n".join(parts) + "\n"


def email_html(digest):
    esc = html.escape
    coverage = digest["coverage"]
    parts = [
        f'<html><body style="font-family:Arial,sans-serif;line-height:1.6;max-width:760px;margin:auto;color:#17251f"><h1>{esc(digest["subject"])}</h1>',
        f"<p>Your daily global / US / India reading brief. Window: last 24 hours, prepared {esc(digest['generated_at'])}.</p>",
        f"<p><strong>Coverage:</strong> {coverage['headlines']} unique headlines considered; {coverage['article_excerpts']} article excerpts, {coverage['feed_excerpts']} publisher feed excerpts, {coverage['headline_only']} headline-only items.</p>",
    ]
    for section in digest["sections"]:
        parts.append(f"<h2>{esc(section['label'])}</h2>")
        for bullet in section["bullets"]:
            parts.append(
                f"<p><strong>{esc(bullet['text'])}</strong><br><em>Why it may matter:</em> {esc(bullet['why_it_matters'])}</p><ul>"
            )
            for source in bullet["sources"]:
                url = news_reader.safe_link(source["url"])
                if not url:
                    raise ValueError("Unsafe citation URL")
                parts.append(
                    f'<li><a href="{esc(url, quote=True)}">{esc(source["title"])}</a> — {esc(source["publisher"])}; {esc(source["published_at"])}; {esc(source["read_status"].replace("_", " "))}</li>'
                )
            parts.append("</ul>")
    parts.append("<h2>Finance terms to learn</h2>")
    for term in digest["glossary"]:
        parts.append(f"<p><strong>{esc(term['term'])}:</strong> {esc(term['meaning'])}</p>")
    parts.append("<h2>Source coverage and limitations</h2><ul>")
    for feed in digest["feeds"]:
        parts.append(
            f"<li>{esc(feed['id'])}: {esc(feed['status'])}"
            + (" (stale)" if feed.get("stale") else "")
            + "</li>"
        )
    parts.append(f'</ul><p style="font-size:12px">{esc(digest["limitations"])}</p></body></html>')
    return "\n".join(parts)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def latest():
    files = sorted(DIGEST_DIR.glob("????-??-??-digest.json"), reverse=True)
    return json.loads(files[0].read_text(encoding="utf-8")) if files else None


def claim_delivery(day):
    # Create-before-send: concurrent bot runs cannot both obtain the same day.
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGEST_DIR / f"{day}-sending.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump({"date_ist": day, "claimed_at": datetime.now(timezone.utc).isoformat()}, output)
    return path
