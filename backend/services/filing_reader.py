"""Read bounded PDF/ZIP filings and extract traceable passages and explicit relationships."""

import hashlib
import io
import re
import zipfile

from bs4 import BeautifulSoup
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from services.document_text import repair_pdf_text
from services.evidence_checks import THIRD_PARTY, issuer_relationship_context, sentence_at
from services.filing_financials import extract_income_table
from services.filing_sources import fetch_public

EXTRACTION_VERSION = 5

CATEGORIES = {
    "operations": (
        "capacity",
        "utilisation",
        "utilization",
        "sales volume",
        "realisation",
        "realization",
        "per tonne",
        "per ton",
        "commissioning",
        "production",
        "captive consumption",
        "EBITDA / T",
        "EBITDA/T",
    ),
    "guidance": (
        "expected",
        "target",
        "proposed",
        "planned",
        "qualification",
        "customer audits",
        "trial production",
        "ramp-up",
        "consent to operate",
        "consent to establish",
    ),
    "concentration": (
        "top 10 customers",
        "top ten customers",
        "top 10 suppliers",
        "top ten suppliers",
        "customer concentration",
        "supplier concentration",
        "no customer having revenue",
    ),
    "supply_chain": (
        "our suppliers",
        "procurement",
        "manufactured in partnership",
        "manufacture and supply",
        "sourcing",
        "customers include",
    ),
    "business": (
        "our business",
        "business model",
        "revenue from",
        "our products",
        "our services",
        "partnership",
        "collaboration",
    ),
    "demand": (
        "demand",
        "subscribers",
        "order book",
        "capacity utilisation",
        "same store",
        "market share",
        "volume growth",
    ),
    "risks": ("risk factors", "dependence", "concentration", "adversely affect", "competition"),
    "governance": ("related party", "auditor", "contingent liabilities", "capital allocation"),
    "financials": (
        "cash flows",
        "balance sheet",
        "working capital",
        "revenue from operations",
        "borrowings",
    ),
    "policy": (
        "regulatory",
        "government policy",
        "interest rate",
        "foreign exchange",
        "tariff",
        "subsid",
    ),
    "competition": (
        "our competitors",
        "competitive landscape",
        "competition",
        "competing",
        "industry overview",
    ),
}
LEGAL_NAME = r"(?:[A-ZÀ-ÖØ-Þ][\w&-]*|[a-zà-öø-ÿ][\w&-]*[A-Z][\w&-]*)(?:\s+(?:[A-Z][\w&-]*|\(India\)|and)){0,8}\s+(?:Private\s+)?Limited"
LEGAL_SUPPLIER = re.compile(
    r"(?P<name>"
    + LEGAL_NAME
    + r")\s+pursuant to (?:the )?(?:manufacture and supply|sale and purchase) agreement"
)
MANUFACTURER = re.compile(r"manufactured in partnership with\s+(?P<name>" + LEGAL_NAME + r")")


def normalize_text(text):
    return " ".join(repair_pdf_text(text).split())


def identity_matches(profile, text):
    ignored = {"limited", "ltd", "india", "company", "corporation", "private", "the", "and"}
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", profile["name"].lower())
        if len(token) >= 3 and token not in ignored
    ]
    if not tokens:
        return False
    normalized = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
    # Name tokens must form the issuer name, not occur independently in industry prose.
    pattern = r"\b" + r"(?:\s+(?:india|private|the|and))*\s+".join(map(re.escape, tokens)) + r"\b"
    return bool(re.search(pattern, normalized))


def _pdfs(content):
    if content.startswith(b"%PDF"):
        return [("document.pdf", content)]
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise ValueError("Source is not a readable PDF or ZIP containing a PDF.")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = [
            entry
            for entry in archive.infolist()
            if entry.filename.lower().endswith(".pdf") and not entry.is_dir()
        ]
        if not entries:
            raise ValueError("The archive contains no PDF report.")
        # Read in memory: never extract archive paths to the filesystem.
        if sum(entry.file_size for entry in entries) > 48_000_000:
            raise ValueError("Archive exceeds the uncompressed document limit.")
        selected = sorted(entries, key=lambda entry: entry.file_size, reverse=True)[:3]
        return [(entry.filename, archive.read(entry)) for entry in selected]


def explicit_relationships(text, source):
    """Only direct language patterns create automatic nodes; general mentions do not."""
    nodes = []

    def add(name, direction, relationship, start, end, category):
        name = re.sub(r"(?:\s+(?:and|of|for|the|de)|\s*&)+$", "", name.strip(" ,;:\n.")).strip()
        if not 2 <= len(name) <= 110:
            return
        if name.casefold() in {
            "ngo",
            "ngos",
            "st",
            "the",
            "government",
            "partners",
            "companies",
            "suppliers",
        }:
            return
        contract_fragment = category in {
            "Contract manufacturer / supplier",
            "Named customer (table)",
            "Named supplier (table)",
        }
        entity = re.search(re.escape(name), text[start:end], re.I)
        anchor = start + entity.start() if entity else start
        if not issuer_relationship_context(
            text, anchor, end, source.get("issuer_terms", []), contract_fragment
        ):
            return
        quote = sentence_at(text, start, end)
        if len(quote) > 2400:
            # Keep the actual relation span when PDF punctuation makes a very long sentence.
            quote = text[max(0, start - 200) : min(len(text), end + 250)]
        if direction == "partners" and re.search(
            r"\b(?:CSR|Parivartan|NGO|charit\w*|community|literacy|senior care|philanthrop\w*)\b",
            quote,
            re.I,
        ):
            category = "Community / CSR partner"
            relationship = (
                "Community / CSR collaboration; no commercial counterparty role established"
            )
        nodes.append(
            {
                "id": hashlib.sha256((source["id"] + direction + name).encode()).hexdigest()[:20],
                "name": name,
                "direction": direction,
                "category": category,
                "relationship": relationship,
                "evidence_status": "filing_extracted",
                "source_id": source["id"],
                "source_url": source["url"],
                "source_title": source["title"],
                "source_date": source.get("date"),
                "source_page": source["page"],
                "evidence_quote": quote,
                "note": "Extracted from explicit report language. Historical disclosure; verify the cited page, context and current status. No financial exposure is inferred.",
            }
        )

    for pattern in (LEGAL_SUPPLIER, MANUFACTURER):
        for match in pattern.finditer(text):
            add(
                match["name"],
                "upstream_suppliers",
                "Disclosed manufacturing / purchase arrangement",
                match.start(),
                match.end(),
                "Contract manufacturer / supplier",
            )
    partner_pattern = re.compile(
        r"(?:[Pp]artnered|[Cc]ollaborated|partnership|collaboration|alliance)\s+with\s+(?P<name>[A-ZÀ-ÖØ-Þ][\w&’'.-]*(?:\s+(?:[A-ZÀ-ÖØ-Þ][\w&’'.-]*|\(India\)|&|of|and|for|the|de)){0,12})"
    )
    for match in partner_pattern.finditer(text):
        if any(
            node["name"].casefold() == match["name"].casefold()
            and node["direction"] == "upstream_suppliers"
            for node in nodes
        ):
            continue
        add(
            match["name"],
            "partners",
            "Partnership / collaboration described in the report",
            match.start(),
            match.end(),
            "Disclosed collaboration",
        )
    brand_pattern = re.compile(
        r"(?:sourcing|procurement|purchase|procure)[^.]{0,180}?brands (?:including|such as)\s+(?P<names>[^.;]{3,180}?)(?:\s+as well as|\.|;)",
        re.I,
    )
    for match in brand_pattern.finditer(text):
        for name in re.split(r",\s*|\s+and\s+", match["names"]):
            if re.fullmatch(r"[A-Z][A-Za-z0-9 &'-]{1,45}", name.strip()):
                add(
                    name,
                    "upstream_suppliers",
                    "Brand named in the company's procurement description",
                    match.start(),
                    match.end(),
                    "Disclosed sourcing brand",
                )
    customers = re.compile(
        r"(?:rent|sell|provide)[^.]{0,90}?\bto (?:our )?(?P<name>subscribers|consumers|households|enterprise customers|retail customers|business customers)\b",
        re.I,
    )
    for match in customers.finditer(text):
        add(
            match["name"].capitalize(),
            "downstream_customers",
            "Customer group described in the filing",
            match.start(),
            match.end(),
            "Disclosed customer segment",
        )
    # Direct named lists establish a role; logos and general mentions do not.
    named_lists = re.compile(
        r"\b(?P<role>customers?|suppliers?)\s+(?:include|including|such as)\s+(?P<names>[^;]{3,600}?)(?=;|(?<!Co)(?<!St)\.(?:\s|$))",
        re.I,
    )
    generic = {
        "customers",
        "suppliers",
        "oems",
        "dealers",
        "distributors",
        "retailers",
        "households",
        "consumers",
        "others",
        "other companies",
        "institutional buyers",
    }
    for match in named_lists.finditer(text):
        role = (
            "downstream_customers"
            if match["role"].lower().startswith("customer")
            else "upstream_suppliers"
        )
        parts = []
        for chunk in re.split(r",\s*(?![^()]*\))", match["names"]):
            if re.search(
                r"\b(?:Limited|Ltd|Inc|LTDA|LLP|GmbH|PLC|Eireli|Corporation|Corp)\b", chunk, re.I
            ):
                marked = re.sub(
                    r"\b(Limited|Ltd\.?|Inc\.?|LTDA|LLP|GmbH|PLC|Eireli|Corporation|Corp\.?)\s+and\s+",
                    r"\1|SPLIT|",
                    chunk,
                    flags=re.I,
                )
                parts.extend(marked.split("|SPLIT|"))
            else:
                parts.extend(re.split(r"\s+and\s+", chunk))
        for part in parts:
            name = re.split(
                r"\s+(?:provides?|supports?|are|is|have|with whom|which|who|that)\b",
                part,
                maxsplit=1,
            )[0].strip(" *:,")
            first_word = name.split()[0] if name else ""
            if not first_word or (
                not first_word[0].isupper()
                and sum(character.isupper() for character in first_word) < 2
            ):
                continue
            if name.casefold() in {"company limited", "power private limited", "private limited"}:
                continue
            if re.search(
                r"^(?:our|other|several|these|such|the|for|including|among|various)\b", name, re.I
            ):
                continue
            if (
                name.casefold() in generic
                or not re.fullmatch(r"[\wÀ-ž&’'(). -]{2,110}", name)
                or not any(c.isupper() for c in name)
            ):
                continue
            add(
                name,
                role,
                "Named in an explicit issuer customer/supplier list",
                match.start(),
                match.end(),
                "Named customer" if role == "downstream_customers" else "Named supplier",
            )
    # Numbered customer/supplier tables: names are read only from an issuer-owned
    # role table, never from anonymous Customer No. entries or numeric weights.
    table = re.search(r"name of (?:the )?(?P<role>customer|supplier)\b", text, re.I)
    if table:
        prefix = text[max(0, table.start() - 850) : table.start()]
        owned = re.search(
            r"\bour\s+(?:top\s+(?:ten|10)\s+)?(?:customers?|suppliers?)\b", prefix, re.I
        ) or (table.start() < 100 and source.get("continued_table_role") == table["role"].lower())
        if owned and not THIRD_PARTY.search(prefix):
            direction = (
                "downstream_customers"
                if table["role"].lower() == "customer"
                else "upstream_suppliers"
            )
            for row in re.finditer(
                r"\b\d{1,2}\.\s+(?P<name>[\wÀ-ž&’'(). -]{2,100}?)\s+\(?[\d,]+\.\d{1,2}\)?\s+\d{1,2}\.\d{1,2}\b",
                text[table.end() :],
            ):
                name = row["name"].strip(" .")
                if re.search(r"customer\s*(?:no|number)|supplier\s*(?:no|number)", name, re.I):
                    continue
                start = table.end() + row.start()
                previous_count = len(nodes)
                add(
                    name,
                    direction,
                    "Named in an issuer counterparty table; no exposure weight inferred",
                    start,
                    table.end() + row.end(),
                    "Named customer (table)"
                    if direction == "downstream_customers"
                    else "Named supplier (table)",
                )
                if len(nodes) > previous_count:
                    quote = text[table.start() : table.end() + row.end()]
                    if len(quote) <= 2400:
                        nodes[-1]["evidence_quote"] = quote
                    nodes[-1]["note"] += (
                        " Role is established by the customer/supplier table heading on this page; group ownership and independence are not inferred."
                    )
    return nodes


def _read_pdf(profile, candidate, pdf, final_url, filename):
    document_id = hashlib.sha256(pdf).hexdigest()[:20]
    passages, nodes, total_pages, read_pages, aliases, financial_metrics = [], [], 0, 0, {}, []
    reader = PdfReader(io.BytesIO(pdf), strict=False)
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("The document is password protected.")
    total_pages += len(reader.pages)
    cover = " ".join(normalize_text(page.extract_text() or "") for page in reader.pages[:3])
    if re.search(r"newspaper\s+(?:publication|advertis(?:e)?ment)|copy of newspaper", cover, re.I):
        raise ValueError(
            "Newspaper clippings contain unrelated third-party content and are excluded from issuer analysis."
        )
    if not identity_matches(profile, cover):
        raise ValueError(
            "Document cover does not match the resolved company name; source was not attached."
        )
    previous_table_role = None
    for index, page in enumerate(reader.pages[:700]):
        raw_text = page.extract_text() or ""
        text = normalize_text(raw_text)[:80000]
        read_pages += 1
        source = {
            "id": f"{document_id}:p{index + 1}",
            "url": final_url,
            "page": index + 1,
            "title": candidate.get("title") or filename,
            "date": candidate.get("date"),
            "issuer_terms": [profile["ticker"].split(".")[0], profile["name"].split()[0]],
            "continued_table_role": previous_table_role,
        }
        financial_metrics.extend(extract_income_table(raw_text, source))
        nodes.extend(explicit_relationships(text, source))
        own_table = re.search(
            r"\bour\s+(?:top\s+(?:ten|10)\s+)?(?P<role>customers?|suppliers?)\b", text, re.I
        )
        continued = re.search(r"name of (?:the )?(?P<role>customer|supplier)\b", text[:140], re.I)
        previous_table_role = (
            own_table["role"].lower().rstrip("s")
            if own_table and not THIRD_PARTY.search(text)
            else previous_table_role
            if continued and previous_table_role == continued["role"].lower()
            else None
        )
        for alias in re.finditer(
            r"(?P<full>" + LEGAL_NAME + r")[ ]*\([ ]*[\"“](?P<short>[\w &.-]{2,50})[\"”][ ]*\)",
            text,
        ):
            aliases.setdefault(alias["short"].strip().casefold(), {})[alias["full"]] = index + 1
        lower = text.lower()
        for category, words in CATEGORIES.items():
            hits = [
                (match.start(), word)
                for word in words
                for match in re.finditer(re.escape(word), lower)
            ]
            if not hits:
                continue
            positions = []
            for position, word in sorted(hits):
                if any(abs(position - previous) < 500 for previous, _ in positions):
                    continue
                positions.append((position, word))
                if len(positions) == 3:
                    break
            for position, word in positions:
                excerpt = text[max(0, position - 150) : min(len(text), position + 1150)]
                score = len(set(word for _, word in hits)) + (
                    12
                    if word
                    in (
                        "our suppliers",
                        "procurement",
                        "manufacture and supply",
                        "manufactured in partnership",
                    )
                    else 0
                )
            if re.search(
                r"table of contents|forward.looking statements|do not constitute|red herring prospectus, including the sections|presentation.*disclaimed",
                excerpt,
                re.I,
            ):
                score -= 20
            if re.search(
                r"our business|raw materials and suppliers|our customers|financial performance|business updates|management commentary",
                excerpt,
                re.I,
            ):
                score += 5
            passages.append(
                {
                    **source,
                    "id": f"{source['id']}:{category}:{position}",
                    "category": category,
                    "text": excerpt,
                    "score": score,
                }
            )
    if not passages:
        raise ValueError(
            "No tracked business or financial passages matched in the readable document text."
        )
    # Keep category coverage, then the most relevant passages, rather than only cover-page boilerplate.
    selected, seen = [], set()
    for category in CATEGORIES:
        ranked = sorted(
            (p for p in passages if p["category"] == category),
            key=lambda p: p["score"],
            reverse=True,
        )[:10]
        for passage in ranked:
            if (category, passage["text"]) not in seen:
                selected.append(passage)
                seen.add((category, passage["text"]))
    unique = {}
    self_names = {profile["ticker"].split(".")[0].casefold(), profile["name"].casefold()}
    for node in nodes:
        definitions = aliases.get(node["name"].casefold(), {})
        if len(definitions) == 1:
            full, definition_page = next(iter(definitions.items()))
            node["note"] += (
                f" Short name '{node['name']}' is defined as '{full}' on PDF page {definition_page}."
            )
            node["name"] = full
        if (
            node["name"].casefold() not in self_names
            and node["name"].lower() not in profile["name"].lower()
        ):
            unique.setdefault((node["direction"], node["name"].casefold()), node)
    suppliers = {
        node["name"].casefold()
        for node in unique.values()
        if node["direction"] == "upstream_suppliers"
    }
    unique = {
        key: node
        for key, node in unique.items()
        if not (node["direction"] == "partners" and node["name"].casefold() in suppliers)
    }
    return {
        "id": document_id,
        "extraction_version": EXTRACTION_VERSION,
        "archive_member": filename if filename != "document.pdf" else None,
        "url": final_url,
        "title": candidate.get("title") or "Company filing",
        "date": candidate.get("date"),
        "date_note": "Exchange publication date, when available; financial periods may differ.",
        "discovered_via": candidate.get("discovered_via", "User-supplied official URL"),
        "total_pages": total_pages,
        "pages_read": read_pages,
        "partial": read_pages < total_pages,
        "passages": selected,
        "relationships": list(unique.values())[:30],
        "financial_metrics": financial_metrics,
    }


def read_document(profile, candidate):
    content, final_url, content_type = fetch_public(candidate["url"], profile.get("website") or "")
    if "text/html" in content_type.lower() or content.lstrip()[:100].lower().startswith(
        (b"<html", b"<!doctype html")
    ):
        return read_company_page(profile, candidate, content, final_url)
    errors = []
    for filename, pdf in _pdfs(content):
        try:
            return _read_pdf(profile, candidate, pdf, final_url, filename)
        except (ValueError, PyPdfError) as error:
            errors.append(str(error))
    raise ValueError("; ".join(dict.fromkeys(errors))[:500])


def read_company_page(profile, candidate, content, final_url):
    from urllib.parse import urlsplit

    from services.filing_sources import allowed_host

    # HTML business evidence belongs on the issuer's own reported host, not a
    # newspaper, regulator listing page or unrelated external article.
    if not allowed_host(urlsplit(final_url).hostname, profile.get("website") or "") or not (
        profile.get("website")
        and (urlsplit(final_url).hostname or "").removeprefix("www.")
        == (urlsplit(profile["website"]).hostname or "").removeprefix("www.")
    ):
        raise ValueError("Company business HTML must be on the reported issuer website.")
    soup = BeautifulSoup(content, "html.parser")
    title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else candidate.get("title", "Company business page")
    )
    for element in soup.select(
        "script,style,nav,footer,header,input,button,select,textarea,noscript"
    ):
        element.decompose()
    body = soup.select_one("main,article") or soup.body
    text = normalize_text(body.get_text(" ", strip=True) if body else "")[:60000]
    if (
        len(text) < 150
        or re.search(r"access denied|verify you are human|request rejected", text, re.I)
        or not identity_matches(profile, title + " " + text[:10000])
    ):
        raise ValueError("Company page did not provide readable issuer-matched business evidence.")
    identifier = hashlib.sha256(text.encode()).hexdigest()[:20]
    source = {
        "id": identifier + ":html",
        "page": None,
        "title": title,
        "url": final_url,
        "date": None,
        "issuer_terms": [profile["ticker"].split(".")[0], profile["name"].split()[0]],
    }
    passages = []
    for category, keywords in CATEGORIES.items():
        hits = [(text.lower().find(word), word) for word in keywords if word in text.lower()]
        for position, _word in sorted(hits)[:3]:
            passages.append(
                {
                    **source,
                    "id": f"{identifier}:html:{category}:{position}",
                    "category": category,
                    "text": text[max(0, position - 150) : position + 1500],
                    "score": len(hits),
                }
            )
    return {
        "id": identifier,
        "url": final_url,
        "title": title,
        "date": None,
        "date_note": "Live company website; publication date not supplied. Claims may be promotional or outdated.",
        "source_kind": "company_page",
        "extraction_version": EXTRACTION_VERSION,
        "total_pages": None,
        "pages_read": None,
        "partial": len(text) >= 60000,
        "passages": passages,
        "relationships": explicit_relationships(text, source),
        "financial_metrics": [],
        "body_text": text,
        "discovered_via": candidate.get("discovered_via", "Company website"),
    }
