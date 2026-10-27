"""Build company networks from collected sources, without a saved company map."""

from services.research_workflow import cached_research, corpus_fingerprint
from services.value_chain_context import sector_context


def build_relationship_network(profile, research=None):
    research = research if research is not None else cached_research(profile["ticker"])
    result = {
        "upstream_suppliers": [],
        "downstream_customers": [],
        "partners": [],
        "data_source": "live_filing_research",
        "research_status": research["status"],
        "research_progress": research.get("progress"),
        "documents_read": len(research["documents"]),
        "research_leads": {"upstream_suppliers": [], "downstream_customers": [], "partners": []},
        "message": "Relationships come from documents collected for this issuer, with source passages and PDF pages. Extraction is partial and historical: a mention does not prove current contract status, completeness or financial exposure.",
        "sector_context": sector_context(profile.get("sector", ""), profile.get("industry", "")),
    }
    seen = set()
    nodes = [node for document in research["documents"] for node in document["relationships"]]
    if research.get("ai_corpus_fingerprint") == corpus_fingerprint(research):
        nodes += research.get("ai_relationships", [])
    for node in nodes:
        key = (node["direction"], node["name"].casefold())
        if key not in seen and node["direction"] in (
            "upstream_suppliers",
            "downstream_customers",
            "partners",
        ):
            displayed = dict(node)
            if displayed.get("category") == "Disclosed business partner":
                displayed["category"] = "Disclosed collaboration"
            result[node["direction"]].append(displayed)
            seen.add(key)
    return result
