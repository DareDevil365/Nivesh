"""Discover public issuer documents by symbol; no company-specific source catalog."""

import calendar
import ipaddress
import json
import re
import socket
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urldefrag, urlencode, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

MAX_DOWNLOAD = 24_000_000
OFFICIAL_DOMAINS = ("nseindia.com", "sebi.gov.in", "bseindia.com")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NiveshResearch/1.0)",
    "Accept": "application/json,text/html,application/pdf,*/*",
    "Referer": "https://www.nseindia.com/",
}


def allowed_host(host, website, extra_domains=()):
    host = (host or "").lower().rstrip(".")
    company = (urlsplit(website or "").hostname or "").lower().removeprefix("www.")
    company = (
        company if "." in company and company not in {"co.in", "com.au", "co.uk", "gov.in"} else ""
    )
    domains = (*OFFICIAL_DOMAINS, *extra_domains, *((company,) if company else ()))
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def validate_source_url(url, website, extra_domains=()):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Use a public HTTPS company, NSE, BSE or SEBI document URL.")
    if not allowed_host(parsed.hostname, website, extra_domains):
        raise ValueError(
            "Source must be on the company's reported website or an official NSE, BSE or SEBI domain."
        )
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise ValueError(
                "Private or local network addresses cannot be used as research sources."
            )
    except OSError as error:
        raise ValueError("The source host could not be resolved.") from error
    return url


def fetch_public(url, website, max_bytes=MAX_DOWNLOAD, extra_domains=()):
    """Bound streamed bytes and validate every redirect before following it."""
    started = time.monotonic()
    with httpx.Client(
        headers=HEADERS, timeout=httpx.Timeout(20, connect=8), trust_env=False
    ) as client:
        for _ in range(4):
            validate_source_url(url, website, extra_domains)
            with client.stream("GET", url) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                response.raise_for_status()
                declared = response.headers.get("content-length", "")
                if declared.isdigit() and int(declared) > max_bytes:
                    raise ValueError("Document exceeds the bounded download size.")
                chunks, size = [], 0
                for chunk in response.iter_bytes(65536):
                    size += len(chunk)
                    if size > max_bytes or time.monotonic() - started > 60:
                        raise ValueError("Source exceeded the download size or time limit.")
                    chunks.append(chunk)
                return b"".join(chunks), url, response.headers.get("content-type", "")
    raise ValueError("Too many document redirects.")


def document_links(html, base):
    if html.startswith("https://") and re.search(r"\.(pdf|zip)(?:[?#]|$)", html, re.I):
        return [{"url": html, "title": "Company document"}]
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for element in soup.select("a[href],iframe[src]"):
        raw = element.get("href") or element.get("src") or ""
        target = urljoin(base, raw)
        query = parse_qs(urlsplit(target).query)
        if "file" in query:
            target = urljoin(base, query["file"][0])
        label = element.get_text(" ", strip=True)[:180]
        document_endpoint = re.search(
            r"/(?:doc|document|download)/(?:\d+|[^/?]+)(?:[/?#]|$)", urlsplit(target).path, re.I
        )
        if (
            re.search(r"\.(pdf|zip)(?:[?#]|$)", target, re.I)
            or (
                document_endpoint
                and re.search(
                    r"report|presentation|transcript|financial|result|prospectus|disclosure",
                    label,
                    re.I,
                )
            )
            or element.get("type") == "application/pdf"
        ):
            found.append(
                {
                    "url": target,
                    "title": label or "Company document",
                }
            )
    # Some investor sites embed PDF URLs in JSON instead of anchor tags.
    clean = html.replace("\\/", "/").replace("\\u002F", "/")
    for target in re.findall(
        r'https://[^\s<>"\x27]+?\.(?:pdf|zip)(?:\?[^\s<>"\x27]*)?', clean, re.I
    ):
        found.append({"url": target, "title": "Company document"})
    return found


def _date(value):
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%d-%B-%Y %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except (ValueError, TypeError):
            continue
    return None


def document_kind(item):
    text = (item.get("title", "") + " " + item["url"]).lower()
    if item.get("source_kind") == "company_page":
        return "business"
    if re.search(
        r"date of board meeting|intimation.*meeting|proceedings.*meeting|voting result|scrutini[sz]er|srutini[sz]er|invitation|audio|newspaper|trading.window|certificate under|investor meet|schedule.*call",
        text,
    ):
        return "administrative"
    if re.search(r"annual[ _-]*report", text):
        return "annual"
    if "prospectus" in text or "rhp" in text:
        return "prospectus"
    if "transcript" in text:
        return "transcript"
    if "brochure" in text:
        return "business"
    if "presentation" in text:
        return "presentation"
    if "financial" in text or "result" in text:
        return "results"
    return "other"


def reporting_period_hint(item):
    """A sorting hint inferred from a label, never a publication date or audited period."""
    text = item.get("title", "")
    months = {name.lower(): index for index, name in enumerate(calendar.month_abbr) if name}
    months.update({name.lower(): index for index, name in enumerate(calendar.month_name) if name})
    for match in re.finditer(r"\b([A-Za-z]{3,9})\s*[- /]?\s*(20\d{2})\b", text):
        month = months.get(match[1].lower())
        if month:
            year = int(match[2])
            return f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"
    quarter = re.search(r"\bQ([1-4])\s*FY\s*['’]?(\d{4}|\d{2})\b", text, re.I)
    if quarter:
        year = int(quarter[2]) + (2000 if len(quarter[2]) == 2 else 0)
        number = int(quarter[1])
        month = (6, 9, 12, 3)[number - 1]
        year -= number != 4
        return f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"
    years = re.findall(r"\b20\d{2}\b", text)
    return max(years) + "-03-31" if years and document_kind(item) == "annual" else ""


def _priority(item):
    text = (item.get("title", "") + " " + item["url"]).lower()
    return (
        {
            "annual": 100,
            "prospectus": 95,
            "presentation": 75,
            "results": 70,
            "transcript": 65,
            "business": 60,
            "other": 20,
            "administrative": -20,
        }[document_kind(item)]
        - (60 if "abridged" in text else 0)
        + (1 if item.get("source_kind") == "company_page" else 0)
    )


def discover_documents(profile):
    website = profile.get("website") or ""
    symbol = profile["ticker"].removesuffix(".NS")
    candidates, attempts = [], []

    def get_json(label, path):
        url = "https://www.nseindia.com/api/" + path
        try:
            raw, _, _ = fetch_public(url, website, 4_000_000)
            data = json.loads(raw)
            attempts.append({"source": label, "status": "checked", "url": url})
            return data
        except (httpx.HTTPError, ValueError) as error:
            attempts.append(
                {
                    "source": label,
                    "status": "unavailable",
                    "url": url,
                    "message": type(error).__name__ + ": source did not return usable public data.",
                }
            )
            return {}

    def belongs_to_issuer(row):
        if not isinstance(row, dict):
            return False
        reported = row.get("symbol") or row.get("sm_symbol")
        if reported and str(reported).upper() != symbol.upper():
            attempts.append(
                {
                    "source": "Exchange issuer metadata",
                    "status": "rejected",
                    "message": "A returned row belongs to a different exchange symbol.",
                }
            )
            return False
        return True

    if profile["ticker"].endswith(".NS"):
        annual = get_json(
            "NSE annual reports",
            "annual-reports?" + urlencode({"index": "equities", "symbol": symbol}),
        )
        rows = annual.get("data", []) if isinstance(annual, dict) else []
        for row in rows[:3]:
            if belongs_to_issuer(row) and row.get("fileName"):
                candidates.append(
                    {
                        "url": row["fileName"],
                        "title": f"Annual report {row.get('fromYr', '')}–{row.get('toYr', '')}",
                        "date": _date(row.get("broadcast_dttm")),
                        "discovered_via": "NSE annual reports",
                    }
                )
        ipo = get_json(
            "NSE IPO documents",
            "ipo-detail?" + urlencode({"symbol": symbol, "series": "EQ", "type": "Forthcoming"}),
        )
        if isinstance(ipo, dict):
            for row in ipo.get("issueInfo", {}).get("dataList", []):
                if re.search(r"prospectus|annual report", row.get("title") or "", re.I):
                    value = row.get("value") or ""
                    links = document_links(value, "https://www.nseindia.com")
                    if value.startswith("https://") and re.search(
                        r"\.(zip|pdf)(?:[?#]|$)", value, re.I
                    ):
                        links.append({"url": value, "title": row["title"]})
                    candidates.extend(
                        {
                            **link,
                            "title": row["title"],
                            "date": None,
                            "discovered_via": "NSE IPO documents",
                        }
                        for link in links
                    )
        today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
        announcements = get_json(
            "NSE recent announcements",
            "corporate-announcements?"
            + urlencode(
                {
                    "index": "equities",
                    "symbol": symbol,
                    "from_date": (today - timedelta(days=365)).strftime("%d-%m-%Y"),
                    "to_date": today.strftime("%d-%m-%Y"),
                }
            ),
        )
        if isinstance(announcements, list):
            for row in announcements[:40]:
                if not belongs_to_issuer(row):
                    continue
                url = row.get("attchmntFile", "")
                if url.startswith("https://"):
                    candidates.append(
                        {
                            "url": url,
                            "title": row.get("attchmntText")
                            or row.get("desc")
                            or "Exchange announcement",
                            "date": _date(row.get("an_dt")),
                            "discovered_via": "NSE recent announcements",
                        }
                    )
    if website:
        if website.startswith("http://"):
            website = "https://" + website[7:]
        queue = [website]
        visited = set()
        while queue and len(visited) < 7:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                raw, final, _ = fetch_public(url, website, 4_000_000)
                html = raw.decode("utf-8", errors="replace")
                candidates.extend(
                    {**link, "date": None, "discovered_via": "Company website"}
                    for link in document_links(html, final)
                )
                soup = BeautifulSoup(html, "html.parser")
                for anchor in soup.select("a[href]"):
                    if anchor["href"].strip().startswith(("#", "javascript:", "mailto:", "tel:")):
                        continue
                    link = urljoin(final, anchor["href"])
                    text = anchor.get_text(" ", strip=True) + " " + link
                    if (
                        allowed_host(urlsplit(link).hostname, website)
                        and re.search(
                            r"our.organization|company.profile|our.business|about.us|our.company|the.\w+.story",
                            text,
                            re.I,
                        )
                        and not re.search(r"\.(pdf|zip)(?:[?#]|$)", link, re.I)
                    ):
                        candidates.append(
                            {
                                "url": link,
                                "title": anchor.get_text(" ", strip=True)
                                or "Company business page",
                                "date": None,
                                "discovered_via": "Company website",
                                "source_kind": "company_page",
                            }
                        )
                    if (
                        allowed_host(urlsplit(link).hostname, website)
                        and re.search(
                            r"investor|annual.report|financial|ipo.disclosure|presentation|transcript|earnings",
                            text,
                            re.I,
                        )
                        and link not in visited
                    ):
                        if link not in queue and not re.search(
                            r"\.(pdf|zip)(?:[?#]|$)|/(?:doc|download)/\d+", link, re.I
                        ):
                            queue.append(link)
                attempts.append({"source": "Company website", "status": "checked", "url": final})
            except (httpx.HTTPError, ValueError):
                attempts.append(
                    {
                        "source": "Company website",
                        "status": "unavailable",
                        "url": url,
                        "message": "Public page could not be read; it may require JavaScript or block automated access.",
                    }
                )
    unique = {}
    for item in candidates:
        item = {**item, "url": urldefrag(item["url"])[0]}
        published = item.get("date")
        if published and datetime.fromisoformat(published).date() > datetime.now(
            timezone.utc
        ).date() + timedelta(days=1):
            attempts.append(
                {
                    "source": item.get("discovered_via"),
                    "status": "rejected",
                    "url": item["url"],
                    "message": "The source publication date is in the future.",
                }
            )
            continue
        if allowed_host(urlsplit(item["url"]).hostname, website):
            unique.setdefault(item["url"], item)
    return sorted(
        unique.values(),
        key=lambda item: (_priority(item), item.get("date") or reporting_period_hint(item)),
        reverse=True,
    ), attempts
