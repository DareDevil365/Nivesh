"""Conservative text checks shared by deterministic and AI relationship extraction.

These are rejection rules, not a semantic verifier. Ambiguous mentions stay in
the evidence passages rather than becoming graph edges.
"""

import re

UNCERTAIN = re.compile(
    r"\b(?:no|not|never|without|neither|ceased|stopped|terminated|termination|"
    r"expired|cancelled|canceled|former|proposed|potential|considering|exploring|"
    r"intend|intends|intended|plan|plans|planned|may|might|could|would|will|"
    r"subject to|non.binding|memorandum of understanding)\b",
    re.I,
)
THIRD_PARTY = re.compile(
    r"\b(?:competitor[s']*|parent company|parent group|holding company|"
    r"group compan(?:y|ies)|industry example|other companies)\b|"
    r"\bour\s+(?:supplier|customer|client|subsidiary|associate|lender|partner)\s+(?:has|have|is|was|announced|entered|formed|partnered)",
    re.I,
)


def sentence_at(text, start, end):
    # Decimal points and initials do not end sentences. PDF whitespace is normalized upstream.
    breaks = [
        match
        for match in re.finditer(r"[.!?;](?:\s+|$)", text)
        if not (
            match.group().startswith(".")
            and re.search(r"\b(?:St|Ltd|Inc|Dr|Mr|Mrs|Co)$", text[: match.start()], re.I)
        )
    ]
    left = max((match.end() for match in breaks if match.end() <= start), default=0)
    right = min((match.start() + 1 for match in breaks if match.start() >= end), default=len(text))
    return text[left:right].strip()


def issuer_relationship_context(text, start, end, issuer_terms=(), allow_contract_fragment=False):
    sentence = sentence_at(text, start, end)
    if UNCERTAIN.search(sentence) or THIRD_PARTY.search(sentence):
        return False
    # Require an issuer subject in this sentence, not in an adjacent paragraph.
    prefix = sentence[: max(0, sentence.find(text[start:end]))]
    if re.search(r"\b(?:we|our|us)\b", prefix, re.I):
        return True
    if re.search(r"\b(?:the|our) company\b", prefix, re.I):
        return True
    for term in issuer_terms:
        if term and re.search(r"(?:^|[,;:]\s*)" + re.escape(term) + r"\b", prefix, re.I):
            return True
    # A report's explicit legal-counterparty contract list may omit 'we'.
    return allow_contract_fragment


def ai_relationship_supported(quote, name, direction, issuer_terms=()):
    """Check each entity occurrence in its own sentence; reject ambiguous roles."""
    patterns = {
        "upstream_suppliers": r"suppl|sourc|procur|manufactur|vendor|purchas",
        "downstream_customers": r"customer|client|subscriber|consumer|sell|sales|sold|rental",
        "partners": r"partner|alliance|collaborat|joint venture",
    }
    for match in re.finditer(re.escape(name), quote, re.I):
        sentence = sentence_at(quote, match.start(), match.end())
        if not issuer_relationship_context(quote, match.start(), match.end(), issuer_terms):
            continue
        # Inspect the relationship clause, not an unrelated role in the next sentence.
        if direction == "upstream_suppliers" and re.search(
            r"\bwe\b[^.;]{0,80}\b(?:supply|sell|provide)\b[^.;]{0,100}\bto\s+" + re.escape(name),
            sentence,
            re.I,
        ):
            continue
        if direction == "downstream_customers" and re.search(
            r"\bwe\b[^.;]{0,80}\b(?:purchase|procure|buy|source)\b[^.;]{0,100}\bfrom\s+"
            + re.escape(name),
            sentence,
            re.I,
        ):
            continue
        if re.search(patterns[direction], sentence, re.I):
            return True
    return False
