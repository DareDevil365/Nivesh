from typing import Dict, Any, List

# Industry value chain ecosystem mappings for key Indian NSE equities
NSE_SUPPLY_CHAIN_MASTER: Dict[str, Dict[str, Any]] = {
    "TATAMOTORS.NS": {
        "ticker": "TATAMOTORS.NS",
        "name": "Tata Motors Limited",
        "sector": "Automobile & EV",
        "upstream_suppliers": [
            {"ticker": "TATASTEEL.NS", "name": "Tata Steel Ltd", "category": "Raw Steel Body Sheets", "relationship": "Key Raw Material Supplier"},
            {"ticker": "UNOMINDA.NS", "name": "Uno Minda Limited", "category": "Auto Electricals & Lighting", "relationship": "Component Vendor"},
            {"ticker": "EXIDEIND.NS", "name": "Exide Industries Ltd", "category": "Lead-Acid & EV Batteries", "relationship": "Battery Supplier"},
            {"ticker": "MRF.NS", "name": "MRF Limited", "category": "Tyres & Rubber", "relationship": "OEM Tyre Supplier"},
            {"ticker": "BOSCHLTD.NS", "name": "Bosch Limited", "category": "Fuel Injection & Electronics", "relationship": "ECU & Powertrain Supplier"},
        ],
        "downstream_customers": [
            {"name": "State Road Transport Undertakings (STUs)", "category": "Commercial Bus Fleets", "relationship": "Government Procurement"},
            {"name": "Indian Armed Forces & Ministry of Defence", "category": "Logistics Vehicles", "relationship": "Institutional Defense Client"},
            {"ticker": "TATATECH.NS", "name": "Tata Technologies Ltd", "category": "Automotive Engineering", "relationship": "R&D & Software Partner"},
            {"name": "National Dealership Network (Passenger Vehicles)", "category": "Retail Distribution", "relationship": "1,400+ Dealership Outlets"},
        ]
    },
    "RELIANCE.NS": {
        "ticker": "RELIANCE.NS",
        "name": "Reliance Industries Limited",
        "sector": "Energy & Petrochemicals",
        "upstream_suppliers": [
            {"ticker": "ONGC.NS", "name": "Oil & Natural Gas Corp (ONGC)", "category": "Crude Oil Input", "relationship": "Refinery Feedstock Supplier"},
            {"ticker": "LARSEN.NS", "name": "Larsen & Toubro (L&T)", "category": "EPC & Capital Equipment", "relationship": "Refinery & Solar EPC Partner"},
            {"name": "Middle East Crude Exporters (Aramco / ADNOC)", "category": "Imported Heavy Crude", "relationship": "Jamnagar Refinery Feedstock"},
        ],
        "downstream_customers": [
            {"name": "Global Chemical & Polymer Manufacturers", "category": "Polypropylene & PTA", "relationship": "Export Bulk Buyers"},
            {"name": "Reliance Jio Subscriber Base (450M+)", "category": "Telecom & Digital Services", "relationship": "B2C Digital Network"},
            {"name": "JioMart & Reliance Retail Stores (18,000+)", "category": "FMCG & Consumer Electronics", "relationship": "B2C Retail Distribution"},
        ]
    },
    "TCS.NS": {
        "ticker": "TCS.NS",
        "name": "Tata Consultancy Services Limited",
        "sector": "IT & Cloud Services",
        "upstream_suppliers": [
            {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "category": "Enterprise Telecom & Connectivity", "relationship": "Network Service Provider"},
            {"name": "Microsoft / AWS / Google Cloud", "category": "Cloud Infrastructure", "relationship": "Cloud Hyperscaler Partners"},
        ],
        "downstream_customers": [
            {"name": "Global Fortune 500 Banks & BFSI Institutions", "category": "Banking Platform (TCS BaNCS)", "relationship": "Core Banking Clients"},
            {"name": "North American & European Enterprise Clients", "category": "IT Managed Services", "relationship": "500+ Active Accounts"},
        ]
    }
}

def get_company_supply_chain(ticker: str) -> Dict[str, Any]:
    """
    Returns Bloomberg SPLC-style Supply Chain & Value Chain Graph for Indian Equities.
    """
    ticker_clean = ticker.upper().strip()
    if ticker_clean in NSE_SUPPLY_CHAIN_MASTER:
        return NSE_SUPPLY_CHAIN_MASTER[ticker_clean]

    # No fabricated data — return honest unavailable state
    symbol_bare = ticker_clean.replace(".NS", "").replace(".BO", "")
    nse_url = f"https://www.nseindia.com/companies-listing/corporate-filings-annual-reports?symbol={symbol_bare}"
    return {
        "ticker": ticker_clean,
        "name": symbol_bare,
        "sector": "NSE Equity",
        "upstream_suppliers": [],
        "downstream_customers": [],
        "data_source": "unavailable",
        "message": (
            f"Detailed supply chain mapping is not yet available for {symbol_bare}. "
            "Currently mapped: TATAMOTORS, RELIANCE, TCS. "
            "View the company's Annual Report for segment & business dependency details."
        ),
        "annual_report_url": nse_url,
    }
