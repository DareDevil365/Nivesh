"""Business-specific diligence prompts, never pre-filled company conclusions."""

PLANS = {
    "steel": [
        (
            "Saleable output and unit economics",
            "Separate finished-product sales from internal transfers; test volume × realised price and EBITDA per tonne. Do not add capacities at successive production stages.",
            [
                "sales volume",
                "realisation",
                "realization",
                "per tonne",
                "per ton",
                "finished products",
            ],
        ),
        (
            "Capacity versus commissioning",
            "Separate installed, proposed, approved and operating capacity; track ramp-up, utilisation, funding and distributor demand.",
            ["capacity", "commission", "utilisation", "utilization", "environment", "distributor"],
        ),
        (
            "Steel spread and policy exposure",
            "Bridge selling prices against ore, coal, scrap, alloy and power costs. Verify products covered by tariffs or PLI, and whether eligibility has produced cash.",
            ["iron ore", "coal", "scrap", "power", "PLI", "import", "tariff"],
        ),
    ],
    "chemicals": [
        (
            "Product mix and qualification",
            "Track product-specific volumes, realisations, customer audits and repeat commercial orders; commissioning does not establish sales.",
            [
                "product mix",
                "qualification",
                "customer audit",
                "commercial",
                "cooling",
                "specialty",
            ],
        ),
        (
            "Feedstock and geography",
            "Trace raw-material origin, inventories, weather disruptions and price pass-through to individual product lines.",
            ["raw material", "flood", "clove", "mint", "procurement", "foreign exchange"],
        ),
        (
            "Plant economics and accounting basis",
            "Separate standalone and consolidated results, depreciation, startup losses and capex. Cash PAT is not operating cash flow.",
            [
                "standalone",
                "consolidated",
                "depreciation",
                "capex",
                "cash flow",
                "utilisation",
                "utilization",
            ],
        ),
    ],
    "precision_manufacturing": [
        (
            "OEM demand and customer exposure",
            "Track equipment cycles, OEM orders and distributors. Preserve anonymous counterparties as undisclosed; a logo is insufficient evidence.",
            ["OEM", "construction", "agricultural", "customer", "distributor"],
        ),
        (
            "Capacity and repricing",
            "Keep fitting-piece capacity separate from forging tonnage. Test utilisation, automation, steel costs and lags in customer price revisions.",
            ["pieces", "forging", "utilisation", "utilization", "price revision", "raw material"],
        ),
        (
            "Export economics and expansion",
            "Verify currency and tariff exposure, subsidiaries and approvals. A proposed overseas entity or land purchase is not completed expansion.",
            ["export", "foreign exchange", "tariff", "subsidiar", "proposed", "land"],
        ),
    ],
    "general": [
        (
            "Demand and unit economics",
            "Identify customers, volumes, realised prices and cost drivers before forecasting revenue or margins.",
            ["customer", "volume", "pricing", "margin"],
        ),
        (
            "Capital and cash conversion",
            "Reconcile earnings, operating cash flow, working capital, reinvestment and dilution over matching periods and bases.",
            ["cash flow", "working capital", "capex", "share capital"],
        ),
    ],
}


def build_research_plan(profile, documents, kind_override=None):
    description = " ".join(
        str(profile.get(key) or "") for key in ("industry", "sector", "about")
    ).lower()
    kind = (
        "steel"
        if "steel" in description
        else "chemicals"
        if "chemical" in description
        else "precision_manufacturing"
        if "hydraulic" in description or "industrial machinery" in description
        else "general"
    )
    if kind_override in PLANS:
        kind = kind_override
    passages = [p for doc in documents for p in doc.get("passages", [])]
    checks = []
    prompts = PLANS[kind] + [
        (
            "What changed since the plan?",
            "Compare older guidance with later filings. Distinguish proposal, approval, incorporation, commissioning, commercial operations and revenue. Filing date and effective event date can differ; similarly named entities may be separate.",
            ["incorporation", "incorporated", "commenced", "commissioned", "completed", "proposed"],
        )
    ]
    for title, question, terms in prompts:
        matches = [p for p in passages if any(term.lower() in p["text"].lower() for term in terms)]
        checks.append(
            {
                "title": title,
                "question": question,
                "evidence_ids": list(dict.fromkeys(p["id"] for p in matches))[:8],
                "status": "evidence_to_review" if matches else "missing_evidence",
                "search_terms": terms,
            }
        )
    return {
        "business_template": kind,
        "classification_basis": "Inferred from provider business description; confirm business fit. Templates contain questions, not company answers.",
        "checks": checks,
    }
