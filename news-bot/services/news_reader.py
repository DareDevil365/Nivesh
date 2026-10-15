"""Personal reading desk: bounded public RSS discovery, never article scraping or AI."""

import hashlib
import html
import re
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

from services.cache_manager import cache_manager


def headline_fingerprint(title):
    normalized = unicodedata.normalize("NFKC", title).casefold()
    # Keep decimal values distinct: 3.0 and 30 must never become the same story.
    tokens = re.findall(r"\d+(?:[.,]\d+)*%?|[^\W\d_]+", normalized, re.UNICODE)
    return hashlib.sha256("|".join(tokens).encode()).hexdigest()


CATEGORIES = {
    "world": {
        "label": "World markets",
        "query": '("global economy" OR "world markets" OR "global stocks")',
        "locale": "US",
        "why": "Start with the broad economic backdrop before individual stocks.",
        "question": "What changed in growth, financing conditions or investor expectations?",
    },
    "us": {
        "label": "US markets",
        "query": '("Wall Street" OR "Federal Reserve" OR "US stock market")',
        "locale": "US",
        "why": "US rates and large companies can influence global funding and risk appetite.",
        "question": "Is this about earnings, interest rates, or a change in expectations?",
    },
    "india": {
        "label": "India",
        "query": '(Sensex OR Nifty OR RBI OR "Indian economy")',
        "locale": "IN",
        "why": "Connect the global backdrop to Indian markets and domestic demand.",
        "question": "Which Indian sectors or businesses have an evidenced exposure?",
    },
    "policy": {
        "label": "Policy & economy",
        "query": '("central bank" OR inflation OR tariffs OR "interest rates")',
        "locale": "US",
        "why": "Policy and inflation can change borrowing costs, demand and trade conditions.",
        "question": "Is this a proposal, a decision, or a rule already in effect?",
    },
    "commodities": {
        "label": "Commodities",
        "query": '("crude oil" OR "gold prices" OR "natural gas")',
        "locale": "US",
        "why": "Input prices can affect producers and consumers differently.",
        "question": "Who pays the higher cost, who benefits, and can the cost be passed on?",
    },
    "events": {
        "label": "World events",
        "query": '(geopolitics OR "trade war" OR "shipping disruption" OR "world news")',
        "locale": "US",
        "why": "Look for disruptions to trade, energy, logistics or customer activity.",
        "question": "What is the actual business exposure, duration and alternative explanation?",
    },
}
GLOSSARY = [
    {
        "term": "Inflation",
        "meaning": "A change in the general price level. Check which measure, period and comparison the report uses.",
    },
    {
        "term": "Interest rate",
        "meaning": "The cost of borrowing. Policy rates, lending rates and bond yields are related but different.",
    },
    {
        "term": "Bond yield",
        "meaning": "A bond's implied return at its current price. A higher yield is not automatically good for every company.",
    },
    {
        "term": "Fed / RBI",
        "meaning": "The US Federal Reserve and Reserve Bank of India. Read the decision separately from commentary about what it might mean.",
    },
    {
        "term": "Tariff",
        "meaning": "A tax on imports. The effect depends on the product, country, timing and who bears the cost.",
    },
    {
        "term": "Index",
        "meaning": "A basket of securities, such as the S&P 500, Nasdaq, Sensex or Nifty. Its movement is not the performance of every company.",
    },
    {
        "term": "Earnings",
        "meaning": "Reported profits for a stated period and accounting basis. Compare cash flow, one-offs and expectations too.",
    },
]
SOURCES = [
    {
        "name": "Financial Times",
        "url": "https://www.ft.com/",
        "focus": "Global business and finance; some articles require a subscription.",
    },
    {
        "name": "Reuters Markets",
        "url": "https://www.reuters.com/markets/",
        "focus": "Market and business reporting; access depends on the publisher.",
    },
    {
        "name": "BBC Business",
        "url": "https://www.bbc.com/news/business",
        "focus": "Business and economic reporting.",
    },
    {
        "name": "The Guardian Business",
        "url": "https://www.theguardian.com/business",
        "focus": "Business and economy coverage.",
    },
    {
        "name": "Mint",
        "url": "https://www.livemint.com/",
        "focus": "Indian business and markets; some articles require a subscription.",
    },
    {
        "name": "Economic Times",
        "url": "https://economictimes.indiatimes.com/",
        "focus": "Indian markets, companies and the economy; some articles require a subscription.",
    },
]
_lock = threading.Lock()
_active = set()
_slots = threading.BoundedSemaphore(4)


def clean_text(value, limit=500):
    value = html.unescape(value or "")
    if "<" in value and ">" in value:
        value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return " ".join(value.split())[:limit]


def safe_link(value):
    try:
        parsed = urlsplit(value or "")
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            return None
        if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
            return None
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
    except ValueError:
        return None


def parse_date(value):
    if not value:
        return None
    try:
        result = parsedate_to_datetime(value)
    except (ValueError, TypeError):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if result.tzinfo is None:
        return None
    return result.astimezone(timezone.utc)


def name_phrase(name):
    name = re.sub(r"\b(?:limited|ltd|private|pvt)\.?\b", "", name, flags=re.I)
    return " ".join(re.findall(r"[\w&.-]+", name, re.UNICODE))[:160].strip()


def name_matches(text, phrase):
    tokens = re.findall(r"\w+", phrase.casefold())
    return bool(tokens) and bool(
        re.search(r"\b" + r"[\W_]*".join(map(re.escape, tokens)) + r"\b", text.casefold())
    )


def _fetch(url):
    # Only callers' fixed provider URLs reach this function; article URLs are never fetched.
    with httpx.Client(
        timeout=httpx.Timeout(10, connect=4),
        trust_env=False,
        follow_redirects=False,
        headers={"User-Agent": "NiveshPersonalResearch/1.0 (public RSS reader)"},
    ) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            body = bytearray()
            started = time.monotonic()
            for chunk in response.iter_bytes(chunk_size=65536):
                if time.monotonic() - started > 20:
                    raise ValueError("Feed exceeded its reading time budget.")
                body.extend(chunk)
                if len(body) > 1_500_000:
                    raise ValueError("Feed exceeds the reading limit.")
            return bytes(body)


def parse_feed(content, platform="news", days=3, company=None, now=None):
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("Feed declarations are not supported.")
    root = ET.fromstring(content)
    if root.tag != ("rss" if platform == "news" else "{http://www.w3.org/2005/Atom}feed"):
        raise ValueError("Response is not the expected public feed.")
    now = now or datetime.now(timezone.utc)
    atom = "{http://www.w3.org/2005/Atom}"
    nodes = root.findall("./channel/item") if platform == "news" else root.findall(atom + "entry")
    results, seen = [], set()
    skipped = {
        "out_of_window": 0,
        "unknown_or_future_date": 0,
        "name_not_in_feed_text": 0,
        "invalid_or_duplicate": 0,
    }
    for node in nodes[:100]:
        if platform == "news":
            title = clean_text(node.findtext("title"), 350)
            url = safe_link(node.findtext("link"))
            source = node.find("source")
            publisher = clean_text(source.text if source is not None else "Unknown publisher", 120)
            publisher_url = safe_link(source.get("url") if source is not None else None)
            when = parse_date(node.findtext("pubDate"))
            excerpt = ""
            if publisher and title.endswith(" - " + publisher):
                title = title[: -(len(publisher) + 3)]
        else:
            title = clean_text(node.findtext(atom + "title"), 350)
            link = node.find(atom + "link")
            url = safe_link(link.get("href") if link is not None else None)
            publisher = "Reddit"
            publisher_url = "https://www.reddit.com/r/IndianStockMarket/"
            when = parse_date(node.findtext(atom + "published") or node.findtext(atom + "updated"))
            excerpt = clean_text(node.findtext(atom + "content"), 1500)
        if not when or when > now + timedelta(minutes=5):
            skipped["unknown_or_future_date"] += 1
            continue
        if when < now - timedelta(days=days):
            skipped["out_of_window"] += 1
            continue
        if company and not name_matches(title + " " + excerpt, company):
            skipped["name_not_in_feed_text"] += 1
            continue
        key = (re.sub(r"\W+", "", title.casefold()), publisher.casefold())
        if not title or not url or key in seen:
            skipped["invalid_or_duplicate"] += 1
            continue
        if platform == "reddit" and urlsplit(url).hostname not in {
            "www.reddit.com",
            "reddit.com",
            "old.reddit.com",
        }:
            skipped["invalid_or_duplicate"] += 1
            continue
        seen.add(key)
        results.append(
            {
                "id": hashlib.sha256((url + title).encode()).hexdigest()[:24],
                "title": title,
                "url": url,
                "publisher": publisher,
                "publisher_url": publisher_url,
                "published_at": when.isoformat(),
                "excerpt": excerpt[:600],
                "platform": platform,
                "evidence_status": "community_claim_unverified"
                if platform == "reddit"
                else "reported_headline_unverified",
                "identity_note": "Company name matched feed text; issuer scope still needs review."
                if company
                else "Topic search; not a company-specific verified fact.",
            }
        )
    results.sort(key=lambda item: item["published_at"], reverse=True)
    return results[:40], skipped, len(nodes)


def feed(query, days=3, locale="US", platform="news", company=None, refresh=False):
    key = (
        "news_v1:"
        + hashlib.sha256(f"{query}:{days}:{locale}:{platform}:{company}".encode()).hexdigest()
    )
    cached = cache_manager.get(key)
    age = time.time() - cached["fetched_epoch"] if cached else float("inf")
    if cached and (
        age < 600
        and not refresh
        or age < 60
        or time.time() - cached.get("last_attempt_epoch", 0) < 60
    ):
        return {**cached, "cached": True, "stale": cached.get("stale", False)}
    with _lock:
        if key in _active or not _slots.acquire(blocking=False):
            return {
                **(cached or {"items": [], "query": query}),
                "status": "busy",
                "stale": bool(cached),
                "message": "Feed checks are busy. Retry shortly.",
            }
        _active.add(key)
    try:
        if platform == "reddit":
            url = "https://www.reddit.com/r/IndianStockMarket/search.rss?" + urlencode(
                {"q": '"' + query + '"', "restrict_sr": "on", "sort": "new"}
            )
        else:
            url = "https://news.google.com/rss/search?" + urlencode(
                {
                    "q": f"{query} when:{days}d",
                    "hl": "en-IN" if locale == "IN" else "en-US",
                    "gl": locale,
                    "ceid": locale + ":en",
                }
            )
        items, skipped, provider_count = parse_feed(_fetch(url), platform, days, company)
        result = {
            "query": query,
            "items": items,
            "status": "available" if items else "no_matches",
            "skipped": skipped,
            "provider_items": provider_count,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "fetched_epoch": time.time(),
            "provider": "Reddit public RSS"
            if platform == "reddit"
            else "Google News RSS (unofficial)",
            "cached": False,
            "stale": False,
        }
        cache_manager.set(key, result, ttl=86400)
        return result
    except (httpx.HTTPError, ET.ParseError, ValueError):
        result = {
            **(cached or {"items": [], "query": query}),
            "status": "unavailable",
            "stale": bool(cached),
            "last_attempt_epoch": time.time(),
            "message": "The public feed could not be read. This does not establish that no news or discussions exist.",
        }
        # Brief negative caching avoids hammering an inaccessible provider.
        if not cached:
            result.update(
                fetched_epoch=time.time(), fetched_at=datetime.now(timezone.utc).isoformat()
            )
        cache_manager.set(key, result, ttl=86400 if cached else 60)
        return result
    finally:
        with _lock:
            _active.discard(key)
            _slots.release()


def priority(item):
    title = item["title"].casefold()
    host = urlsplit(item.get("publisher_url") or "").hostname or ""
    preferred = {
        "reuters.com",
        "ft.com",
        "bloomberg.com",
        "wsj.com",
        "cnbc.com",
        "bbc.com",
        "bbc.co.uk",
        "theguardian.com",
        "apnews.com",
        "cbc.ca",
        "livemint.com",
        "economictimes.indiatimes.com",
        "business-standard.com",
        "thehindu.com",
    }
    form = (
        "analysis_or_question"
        if re.search(
            r"\?|\b(?:opinion|editorial|analysis|explainer|review|forecast|outlook)\b", title
        )
        else "reported_headline"
    )
    if re.search(
        r"\b(?:top|best|\d+)\b.{0,35}\bstocks?\b|stocks? to (?:buy|watch)|stock picks|sponsored|buy these",
        title,
    ):
        form = "stock_picks"
    item = {
        **item,
        "headline_form": form,
        "publisher_preference": any(
            host == domain or host.endswith("." + domain) for domain in preferred
        ),
    }
    if form == "stock_picks":
        return {
            **item,
            "reading_score": 0,
            "why_read": "Headline suggests investment ideas rather than a broad-event report",
            "question": "What is the original evidence and which assumptions or incentives underlie the recommendation?",
        }
    groups = [
        (
            5,
            r"interest rate|central bank|federal reserve|\bfed\b|\brbi\b|inflation|tariff",
            "Economy-wide policy or price conditions",
            "Check the exact decision, reference period and implementation date.",
        ),
        (
            4,
            r"crash|sell.off|recession|surge|slump|record high|war|conflict|oil price|crude",
            "Potential broad market or supply disruption",
            "Separate reported moves from explanations; identify actual business exposures.",
        ),
        (
            3,
            r"earnings|profit|results|gdp|jobs|employment|growth",
            "Earnings or economic activity",
            "Compare the result with previous periods and expectations on the same basis.",
        ),
    ]
    for score, pattern, reason, prompt in groups:
        if re.search(pattern, title):
            return {**item, "reading_score": score, "why_read": reason, "question": prompt}
    return {
        **item,
        "reading_score": 1,
        "why_read": "Recent coverage in this topic",
        "question": "What changed, which source establishes it, and who might be affected?",
    }


def reading_desk(refresh=False):
    def load(entry):
        key, config = entry
        result = feed(config["query"], locale=config["locale"], refresh=refresh)
        return {
            "id": key,
            **config,
            **result,
            "items": [priority(item) for item in result["items"]],
        }

    with ThreadPoolExecutor(max_workers=3) as pool:
        sections = list(pool.map(load, CATEGORIES.items()))
    # Breadth first: one suggested story per region/topic, with exact-title deduplication.
    selected, seen, publishers = [], set(), {}
    for section in sections:
        candidates = sorted(
            section["items"],
            key=lambda item: (
                item["headline_form"] == "reported_headline",
                item["publisher_preference"],
                item["reading_score"],
                item["published_at"],
            ),
            reverse=True,
        )
        for item in candidates:
            if item["headline_form"] == "stock_picks":
                continue
            if not headline_relevant(section["id"], item["title"]):
                continue
            identity = re.sub(r"\W+", "", item["title"].casefold())
            if identity in seen or publishers.get(item["publisher"], 0) >= 2:
                continue
            seen.add(identity)
            publishers[item["publisher"]] = publishers.get(item["publisher"], 0) + 1
            selected.append(
                {**item, "section": section["label"], "reading_order": len(selected) + 1}
            )
            break
    return {
        "sections": sections,
        "start_here": selected,
        "glossary": GLOSSARY,
        "sources": SOURCES,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ranking_note": "Suggested reading order uses topic breadth, headline relevance, a default preference for established news-publisher domains, headline form, keywords and recency. Stock-pick and apparently off-topic headlines are excluded from Start here; apparent analysis/questions follow news-style headlines. These are heuristics, not a verification of credibility, market importance or future prices. Publisher metadata comes from public feeds; article bodies are not read.",
        "limitations": "Free, unofficial English-language RSS discovery can be delayed, incomplete or unavailable; it is not exhaustive global coverage. Headlines are attributed reports, not verified financial facts. Links may open Google News before the publisher. Some publishers require subscriptions. No AI calls are made.",
    }


def headline_relevant(section, title):
    patterns = {
        "world": r"econom|market|stocks?|trade|debt|growth|imf|world bank|inflation|gdp|recession|tariff",
        "us": r"\bu\.?s\.?\b|united states|american|wall street|\bfed\b|federal reserve|s&p|nasdaq|dow jones|treasur",
        "india": r"india|nifty|sensex|\brbi\b|rupee|\bnse\b|\bbse\b",
        "policy": r"central bank|inflation|tariff|rates?|policy|\bfed\b|\brbi\b|\bboe\b|\becb\b",
        "commodities": r"oil|crude|gold|gas|commodit|metal|copper|silver|coal|energy",
        "events": r"war|conflict|trade|shipping|geopolit|sanction|election|government|crisis|attack|peace|supply|disrupt",
    }
    return bool(re.search(patterns.get(section, r"."), title, re.I))


def company_news(profile, days=30, refresh=False):
    phrase = name_phrase(profile["name"])
    if not phrase:
        raise HTTPException(422, "No usable company name for news search.")
    result = feed('"' + phrase + '"', days, "IN", company=phrase, refresh=refresh)
    return {
        **result,
        "ticker": profile["ticker"],
        "company": phrase,
        "search_url": "https://news.google.com/search?"
        + urlencode({"q": '"' + phrase + '"', "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}),
    }


def community(profile, refresh=False):
    phrase = name_phrase(profile["name"])
    return {
        "ticker": profile["ticker"],
        "company": phrase,
        "reddit": feed(phrase, 90, "IN", "reddit", company=phrase, refresh=refresh),
        "x": {
            "status": "search_link_only",
            "url": "https://x.com/search?" + urlencode({"q": '"' + phrase + '"', "f": "live"}),
            "message": "Open X to search. No X posts or sentiment are fetched by this app; access may require login.",
        },
        "reddit_search": "https://www.reddit.com/r/IndianStockMarket/search/?"
        + urlencode({"q": '"' + phrase + '"', "restrict_sr": "on", "sort": "new"}),
        "limitations": "Reddit covers one public community, not all Reddit or complete comment threads. Matching a company name does not verify a claim. Votes, repetition and sentiment do not establish truth. Community content never updates financial inputs, projects or supply-chain edges.",
    }
