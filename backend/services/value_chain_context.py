"""Illustrative industry roles, never company-specific supplier assertions."""

CONTEXTS = [
    (
        ("bank", "financial", "insurance", "capital market"),
        [
            "Depositors and wholesale funding",
            "Payments and technology infrastructure",
            "Credit and risk information",
        ],
        ["Household borrowers and savers", "Business borrowers", "Institutional clients"],
        "Track funding concentration, credit quality, regulatory capital and technology dependence.",
    ),
    (
        ("software", "information technology", "it services", "cloud"),
        [
            "Skilled employees and subcontractors",
            "Cloud and software platforms",
            "Connectivity and data centres",
        ],
        [
            "Financial services clients",
            "Enterprise and public-sector clients",
            "Consumer and industrial clients",
        ],
        "Check disclosed client concentration, contract renewals, subcontracting and platform exposure.",
    ),
    (
        ("auto", "vehicle", "tyre"),
        [
            "Metals and castings",
            "Electronics and powertrain components",
            "Batteries, tyres and materials",
        ],
        ["Dealers and distributors", "Fleet and institutional buyers", "Retail vehicle buyers"],
        "Check single-source components, input prices, dealer inventory and end-market demand.",
    ),
    (
        ("energy", "oil", "gas", "petroleum", "petrochemical"),
        [
            "Feedstock and fuel producers",
            "Equipment and engineering contractors",
            "Transport and storage operators",
        ],
        [
            "Industrial and chemical buyers",
            "Fuel distributors and retailers",
            "Power and commercial users",
        ],
        "Check feedstock origin, commodity spreads, logistics bottlenecks and customer concentration.",
    ),
    (
        ("health", "pharma", "drug", "biotech"),
        [
            "Active ingredients and intermediates",
            "Research and manufacturing partners",
            "Packaging and cold-chain providers",
        ],
        [
            "Distributors and pharmacies",
            "Hospitals and healthcare providers",
            "Export-market buyers",
        ],
        "Check manufacturing dependencies, regulatory inspections, product concentration and reimbursement.",
    ),
    (
        ("consumer", "food", "tobacco", "retail", "jewel", "restaurant"),
        [
            "Agricultural and material inputs",
            "Manufacturing and packaging partners",
            "Warehousing and logistics",
        ],
        [
            "Distributors and wholesale channels",
            "Stores and online marketplaces",
            "Households and business buyers",
        ],
        "Check sourcing concentration, working capital, channel margins and discretionary demand.",
    ),
    (
        ("communication", "telecom"),
        [
            "Network equipment and software",
            "Spectrum, towers and fibre",
            "Power and infrastructure services",
        ],
        [
            "Mobile and broadband subscribers",
            "Enterprise connectivity clients",
            "Digital service partners",
        ],
        "Check vendor concentration, spectrum commitments, subscriber economics and network investment.",
    ),
    (
        ("metal", "steel", "mining", "material", "cement"),
        [
            "Ore, minerals and feedstock",
            "Fuel and power producers",
            "Mining and processing equipment",
        ],
        [
            "Manufacturers and fabricators",
            "Construction and infrastructure buyers",
            "Traders and export customers",
        ],
        "Check resource access, energy costs, freight exposure and downstream demand cycles.",
    ),
    (
        (
            "industrial",
            "defense",
            "defence",
            "aerospace",
            "electronic",
            "engineering",
            "construction",
        ),
        [
            "Materials and specialised components",
            "Equipment and technology partners",
            "Subcontractors and engineering talent",
        ],
        [
            "Industrial and infrastructure customers",
            "Government and institutional buyers",
            "Distributors and export partners",
        ],
        "Check order concentration, execution milestones, component lead times and receivables.",
    ),
]


def sector_context(sector, industry):
    text = f"{industry} {sector}".lower()
    selected = next((row for row in CONTEXTS if any(k in text for k in row[0])), None)
    if selected:
        _, upstream, downstream, question = selected
    else:
        upstream = ["Input and service providers", "People, technology and capital"]
        downstream = ["Distribution and delivery channels", "Business and household customers"]
        question = (
            "Use the annual report to identify material inputs, channels and concentration risks."
        )

    def nodes(names, direction):
        return [
            {
                "id": f"context-{direction}-{i}",
                "name": name,
                "category": "Illustrative industry role",
                "relationship": "Sector context only",
                "evidence_status": "sector_context",
                "source_url": None,
                "source_date": None,
                "note": question,
            }
            for i, name in enumerate(names)
        ]

    return {
        "upstream_suppliers": nodes(upstream, "upstream"),
        "downstream_customers": nodes(downstream, "downstream"),
        "partners": [],
        "research_question": question,
    }
