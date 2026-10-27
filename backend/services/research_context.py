"""Dated primary-source policy leads; relevance is a question, not an impact claim."""

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from services.cache_manager import cache_manager
from services.filing_sources import allowed_host, fetch_public, validate_source_url

CONTEXT_DOMAINS = (
    "pib.gov.in",
    "rbi.org.in",
    "mospi.gov.in",
    "commerce.gov.in",
    "imf.org",
    "worldbank.org",
    "federalreserve.gov",
)
FEEDS = (
    ("PIB government releases", "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3&reg=3"),
    ("RBI press releases", "https://www.rbi.org.in/pressreleases_rss.xml"),
)
MACRO_TERMS = (
    "monetary policy",
    "interest rate",
    "inflation",
    "tariff",
    "trade policy",
    "repo",
    "open market operation",
    "government securities",
)
SECTOR_TERMS = {
    "financial": ("bank", "banks", "credit", "liquidity", "lending"),
    "technology": ("digital", "software", "cybersecurity", "semiconductor"),
    "industrials": ("manufacturing", "infrastructure", "logistics", "industrial"),
    "consumer": ("consumption", "retail", "consumer", "household"),
    "energy": ("oil", "gas", "power", "energy", "renewable"),
    "health": ("health", "pharmaceutical", "medical"),
    "materials": ("steel", "mining", "cement", "metals"),
}


def context_url(url):
    # No company host is accepted here: cross-company context stays distinct from issuer evidence.
    if not allowed_host(urlsplit(url).hostname, "", CONTEXT_DOMAINS) or not any(
        urlsplit(url).hostname == domain or (urlsplit(url).hostname or "").endswith("." + domain)
        for domain in CONTEXT_DOMAINS
    ):
        raise ValueError(
            "Context URLs must be on PIB, RBI, MoSPI, Commerce, IMF, World Bank or Federal Reserve websites."
        )
    return validate_source_url(url, "", CONTEXT_DOMAINS)


def _date(value):
    if not value:
        return None
    try:
        date = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return date.replace(tzinfo=date.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()


def feed_items(raw, feed_url):
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Feed contains unsupported XML declarations.")
    root = ET.fromstring(raw)
    items = []
    for node in root.findall(".//item")[:80]:
        url = (node.findtext("link") or "").strip()
        title = BeautifulSoup(node.findtext("title") or "", "html.parser").get_text(" ", strip=True)
        published = _date(node.findtext("pubDate"))
        if published and datetime.fromisoformat(published) > datetime.now(timezone.utc) + timedelta(
            days=1
        ):
            continue
        if (
            title
            and url.startswith("https://")
            and allowed_host(urlsplit(url).hostname, "", CONTEXT_DOMAINS)
        ):
            items.append(
                {"url": url, "title": title, "date": published, "discovered_via": feed_url}
            )
    return items


def read_context(candidate):
    context_url(candidate["url"])
    raw, final, content_type = fetch_public(candidate["url"], "", 2_000_000, CONTEXT_DOMAINS)
    if "html" not in content_type.lower() and not raw.lstrip().startswith(
        (b"<!DOCTYPE html", b"<html", b"<!doctype html")
    ):
        raise ValueError(
            "Policy context currently accepts public HTML articles; PDF context needs a separate adapter."
        )
    soup = BeautifulSoup(raw, "html.parser")
    # ASP.NET pages often wrap the entire article in a form. Remove controls,
    # not the form container and its source text.
    for tag in soup.select(
        "script, style, nav, footer, header, input, button, select, textarea, noscript"
    ):
        tag.decompose()
    body = (
        soup.select_one(
            "article, main, .innner-page-main-about-us-content-right-part, #pnlPressRelease"
        )
        or soup.body
    )
    if body is None:
        raise ValueError("The policy page has no readable article body.")
    text = " ".join(body.get_text(" ", strip=True).split())[:18000]
    if len(text) < 150 or re.search(
        r"access denied|verify you are human|request rejected|enable javascript.*continue",
        text,
        re.I,
    ):
        raise ValueError(
            "The policy page returned an access challenge or insufficient readable text."
        )
    title_words = set(re.findall(r"[a-z]{4,}", (candidate.get("title") or "").lower()))
    if (
        title_words
        and sum(
            bool(re.search(r"\b" + re.escape(word) + r"\b", text, re.I)) for word in title_words
        )
        / len(title_words)
        < 0.6
    ):
        raise ValueError(
            "The returned article does not match the feed headline; it was not attached."
        )
    identifier = hashlib.sha256((final + text).encode()).hexdigest()[:20]
    published = candidate.get("date")
    if not published:
        metadata = soup.select_one(
            'meta[property="article:published_time"], meta[name="date"], time[datetime]'
        )
        if metadata:
            published = _date(metadata.get("content") or metadata.get("datetime"))
        if not published and (urlsplit(final).hostname or "").endswith("pib.gov.in"):
            stamp = re.search(
                r"\b(\d{1,2} [A-Z]{3} \d{4} \d{1,2}:\d{2}\s*(?:AM|PM))\b", text[:1500]
            )
            if stamp:
                try:
                    published = (
                        datetime.strptime(
                            stamp[1].replace(" PM", "PM").replace(" AM", "AM"), "%d %b %Y %I:%M%p"
                        )
                        .replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                        .isoformat()
                    )
                except ValueError:
                    pass
    return {
        "id": "context:" + identifier,
        "title": candidate.get("title")
        or (
            soup.select_one("h1").get_text(" ", strip=True)
            if soup.select_one("h1")
            else soup.title.get_text(" ", strip=True)
            if soup.title
            else "Official policy source"
        ),
        "url": final,
        "date": published,
        "date_note": "Source-reported publication date; publisher time zone is not independently verified.",
        "date_warning": "Publisher timestamp is later than collection time; verify its time zone."
        if published
        and datetime.fromisoformat(published) > datetime.now(timezone.utc) + timedelta(minutes=20)
        else None,
        "text": text,
        "matched_terms": candidate.get("matched_terms", []),
        "status": "impact_unverified",
        "note": "Official-source context. A keyword match does not establish company exposure, implementation, financial effect or stock-price direction.",
    }


def collect_context(profile, source_urls=()):
    terms = set(MACRO_TERMS)
    for sector, keywords in SECTOR_TERMS.items():
        if sector in (profile.get("sector") or "").lower():
            terms.update(keywords)
    terms.update(
        word
        for word in re.findall(
            r"[a-z][a-z-]{4,}",
            (
                (profile.get("industry") or "")
                + " "
                + (profile.get("sector") or "")
                + " "
                + profile["name"]
            ).lower(),
        )
        if word not in {"limited", "private", "company", "services", "other", "industries"}
    )
    candidates, attempts, errors, articles = [], [], [], []
    for label, url in FEEDS:
        try:
            items = cache_manager.get("context_feed_v1:" + url)
            if items is None:
                raw, _, _ = fetch_public(url, "", 1_000_000, CONTEXT_DOMAINS)
                items = feed_items(raw, url)
                if not items:
                    raise ValueError("Feed did not contain usable public article links.")
                cache_manager.set("context_feed_v1:" + url, items, ttl=3600)
            for item in items:
                matched = sorted(
                    term
                    for term in terms
                    if re.search(r"\b" + re.escape(term) + r"\b", item["title"], re.I)
                )
                if matched:
                    candidates.append({**item, "matched_terms": matched})
            attempts.append({"source": label, "url": url, "status": "checked"})
        except Exception as error:
            attempts.append(
                {
                    "source": label,
                    "url": url,
                    "status": "unavailable",
                    "message": type(error).__name__ + ": official feed could not be read.",
                }
            )
    candidates.sort(
        key=lambda item: (len(item["matched_terms"]), item.get("date") or ""), reverse=True
    )
    manual = [{"url": url, "title": "", "matched_terms": [], "date": None} for url in source_urls]
    seen = set()
    for candidate in manual + candidates:
        if candidate["url"] in seen:
            continue
        if len(seen) >= 5 or len(articles) >= 3:
            break
        seen.add(candidate["url"])
        try:
            articles.append(read_context(candidate))
        except Exception as error:
            errors.append(
                {
                    "url": candidate["url"],
                    "message": str(error)[:300]
                    if isinstance(error, ValueError)
                    else type(error).__name__ + ": policy article could not be read.",
                }
            )
    return {
        "articles": articles,
        "attempts": attempts,
        "errors": errors,
        "candidates": candidates[:15],
        "status": "leads_collected" if articles else "no_readable_context",
        "limitations": "Latest PIB/RBI feed items and supplied official HTML URLs only. Headline matching is partial and may be irrelevant. No global news search, causal impact verification or prediction is performed.",
    }
