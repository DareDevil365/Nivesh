from typing import List, Dict, Any

# Nifty 500 Constituent Universe Master List
NSE_MASTER_LIST: Dict[str, Dict[str, str]] = {
    # NIFTY 50 & IT LEADERS
    "RELIANCE.NS": {"name": "Reliance Industries Ltd", "sector": "Energy", "industry": "Oil & Gas Integrated"},
    "TCS.NS": {"name": "Tata Consultancy Services Ltd", "sector": "Technology", "industry": "IT Services"},
    "INFY.NS": {"name": "Infosys Ltd", "sector": "Technology", "industry": "IT Services"},
    "HDFCBANK.NS": {"name": "HDFC Bank Ltd", "sector": "Financial Services", "industry": "Private Bank"},
    "ICICIBANK.NS": {"name": "ICICI Bank Ltd", "sector": "Financial Services", "industry": "Private Bank"},
    "BHARTIARTL.NS": {"name": "Bharti Airtel Ltd", "sector": "Telecommunication", "industry": "Telecom Services"},
    "SBIN.NS": {"name": "State Bank of India", "sector": "Financial Services", "industry": "Public Bank"},
    "LTIM.NS": {"name": "LTIMindtree Ltd", "sector": "Technology", "industry": "IT Services"},
    "ITC.NS": {"name": "ITC Ltd", "sector": "FMCG", "industry": "Tobacco & Diversified FMCG"},
    "HINDUNILVR.NS": {"name": "Hindustan Unilever Ltd", "sector": "FMCG", "industry": "Household Products"},
    "LT.NS": {"name": "Larsen & Toubro Ltd", "sector": "Capital Goods", "industry": "Engineering & Construction"},
    "AXISBANK.NS": {"name": "Axis Bank Ltd", "sector": "Financial Services", "industry": "Private Bank"},
    "KOTAKBANK.NS": {"name": "Kotak Mahindra Bank Ltd", "sector": "Financial Services", "industry": "Private Bank"},
    "HCLTECH.NS": {"name": "HCL Technologies Ltd", "sector": "Technology", "industry": "IT Services"},
    "WIPRO.NS": {"name": "Wipro Ltd", "sector": "Technology", "industry": "IT Services"},
    "TATAMOTORS.NS": {"name": "Tata Motors Ltd", "sector": "Automobile", "industry": "Auto Manufacturers"},
    "MARUTI.NS": {"name": "Maruti Suzuki India Ltd", "sector": "Automobile", "industry": "Auto Manufacturers"},
    "M&M.NS": {"name": "Mahindra & Mahindra Ltd", "sector": "Automobile", "industry": "Auto Manufacturers"},
    "SUNPHARMA.NS": {"name": "Sun Pharmaceutical Industries Ltd", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    "NTPC.NS": {"name": "NTPC Ltd", "sector": "Utilities", "industry": "Power Generation"},
    "ONGC.NS": {"name": "Oil & Natural Gas Corporation Ltd", "sector": "Energy", "industry": "Oil & Gas Exploration"},
    "POWERGRID.NS": {"name": "Power Grid Corporation of India Ltd", "sector": "Utilities", "industry": "Power Transmission"},
    "TITAN.NS": {"name": "Titan Company Ltd", "sector": "Consumer Durables", "industry": "Gems & Jewellery"},
    "BAJFINANCE.NS": {"name": "Bajaj Finance Ltd", "sector": "Financial Services", "industry": "NBFC"},
    "BAJAJFINSV.NS": {"name": "Bajaj Finserv Ltd", "sector": "Financial Services", "industry": "Financial Holding"},
    "ULTRACEMCO.NS": {"name": "UltraTech Cement Ltd", "sector": "Construction Materials", "industry": "Cement"},
    "ASIANPAINT.NS": {"name": "Asian Paints Ltd", "sector": "Consumer Durables", "industry": "Paints"},
    "ADANIENT.NS": {"name": "Adani Enterprises Ltd", "sector": "Metals & Mining", "industry": "Trading & Mining"},
    "ADANIPORTS.NS": {"name": "Adani Ports and Special Economic Zone Ltd", "sector": "Services", "industry": "Ports & Shipping"},
    "COALINDIA.NS": {"name": "Coal India Ltd", "sector": "Energy", "industry": "Coal"},
    "TATASTEEL.NS": {"name": "Tata Steel Ltd", "sector": "Metals & Mining", "industry": "Iron & Steel"},
    "JSWSTEEL.NS": {"name": "JSW Steel Ltd", "sector": "Metals & Mining", "industry": "Iron & Steel"},
    "HINDALCO.NS": {"name": "Hindalco Industries Ltd", "sector": "Metals & Mining", "industry": "Aluminium"},
    "GRASIM.NS": {"name": "Grasim Industries Ltd", "sector": "Construction Materials", "industry": "Diversified Chemicals"},
    "TECHM.NS": {"name": "Tech Mahindra Ltd", "sector": "Technology", "industry": "IT Services"},
    "CIPLA.NS": {"name": "Cipla Ltd", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    "DRREDDY.NS": {"name": "Dr. Reddy's Laboratories Ltd", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    "APOLLOHOSP.NS": {"name": "Apollo Hospitals Enterprise Ltd", "sector": "Healthcare", "industry": "Hospital Services"},
    "DIVISLAB.NS": {"name": "Divi's Laboratories Ltd", "sector": "Healthcare", "industry": "APIs & Pharma"},
    "EICHERMOT.NS": {"name": "Eicher Motors Ltd", "sector": "Automobile", "industry": "Auto Manufacturers"},
    "HEROMOTOCO.NS": {"name": "Hero MotoCorp Ltd", "sector": "Automobile", "industry": "2 & 3 Wheelers"},
    "BAJAJ-AUTO.NS": {"name": "Bajaj Auto Ltd", "sector": "Automobile", "industry": "2 & 3 Wheelers"},
    "TATACONSUM.NS": {"name": "Tata Consumer Products Ltd", "sector": "FMCG", "industry": "Packaged Foods"},
    "BRITANNIA.NS": {"name": "Britannia Industries Ltd", "sector": "FMCG", "industry": "Packaged Foods"},
    "NESTLEIND.NS": {"name": "Nestle India Ltd", "sector": "FMCG", "industry": "Packaged Foods"},
    "BPCL.NS": {"name": "Bharat Petroleum Corporation Ltd", "sector": "Energy", "industry": "Oil Refining"},
    "IOC.NS": {"name": "Indian Oil Corporation Ltd", "sector": "Energy", "industry": "Oil Refining"},
    "BEL.NS": {"name": "Bharat Electronics Ltd", "sector": "Capital Goods", "industry": "Defence Electronics"},
    "HAL.NS": {"name": "Hindustan Aeronautics Ltd", "sector": "Capital Goods", "industry": "Aerospace & Defence"},
    "VBL.NS": {"name": "Varun Beverages Ltd", "sector": "FMCG", "industry": "Beverages"},
    "DLF.NS": {"name": "DLF Ltd", "sector": "Realty", "industry": "Real Estate Developers"},
    "ZOMATO.NS": {"name": "Zomato Ltd", "sector": "Consumer Services", "industry": "E-Commerce & Food Delivery"},
    "JIOFIN.NS": {"name": "Jio Financial Services Ltd", "sector": "Financial Services", "industry": "NBFC"},
    "PAYTM.NS": {"name": "One 97 Communications Ltd (Paytm)", "sector": "Financial Services", "industry": "Fintech"},
    "POLICYBZR.NS": {"name": "PB Fintech Ltd (Policybazaar)", "sector": "Financial Services", "industry": "Fintech"},
    "NYKAA.NS": {"name": "FSN E-Commerce Ventures Ltd (Nykaa)", "sector": "Consumer Services", "industry": "E-Commerce"},
    "DELHIVERY.NS": {"name": "Delhivery Ltd", "sector": "Services", "industry": "Logistics & Supply Chain"},
    "SUZLON.NS": {"name": "Suzlon Energy Ltd", "sector": "Utilities", "industry": "Renewable Energy"},
    "IRFC.NS": {"name": "Indian Railway Finance Corporation Ltd", "sector": "Financial Services", "industry": "NBFC"},
    "RVNL.NS": {"name": "Rail Vikas Nigam Ltd", "sector": "Capital Goods", "industry": "Railway Infrastructure"},
    "MAZDOCK.NS": {"name": "Mazagon Dock Shipbuilders Ltd", "sector": "Capital Goods", "industry": "Shipbuilding & Defence"}
}

def search_stock_master(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """Fast in-memory fuzzy typeahead search across master list."""
    query = query.strip().upper()
    if not query:
        return []

    query_bare = query.replace(".NS", "").replace(".BO", "")
    results = []

    # 1. Exact Ticker Prefix Match
    for ticker, info in NSE_MASTER_LIST.items():
        ticker_bare = ticker.replace(".NS", "")
        if ticker_bare.startswith(query_bare):
            results.append({
                "ticker": ticker,
                "name": info["name"],
                "sector": info["sector"],
                "industry": info["industry"],
                "score": 100
            })

    # 2. Company Name Word Match
    if len(results) < limit:
        for ticker, info in NSE_MASTER_LIST.items():
            if any(r["ticker"] == ticker for r in results):
                continue
            name_upper = info["name"].upper()
            if query_bare in name_upper:
                results.append({
                    "ticker": ticker,
                    "name": info["name"],
                    "sector": info["sector"],
                    "industry": info["industry"],
                    "score": 80
                })

    # 3. Dynamic Candidate Fallback
    if not results:
        results.append({
            "ticker": f"{query_bare}.NS",
            "name": f"{query_bare} (NSE Equity)",
            "sector": "NSE Equity",
            "industry": "Real-time Fetch",
            "score": 50
        })

    return results[:limit]
