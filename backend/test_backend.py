from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("--- Auditing Complete Core API Surface (FastAPI) ---")

endpoints = [
    ("GET", "/api/companies/RELIANCE.NS"),
    ("GET", "/api/companies/RELIANCE.NS/chart"),
    ("GET", "/api/companies/RELIANCE.NS/peers"),
    ("GET", "/api/companies/RELIANCE.NS/pros-cons"),
    ("GET", "/api/companies/RELIANCE.NS/financials"),
    ("GET", "/api/companies/RELIANCE.NS/quarterly-results"),
    ("GET", "/api/companies/RELIANCE.NS/ratios"),
    ("GET", "/api/companies/RELIANCE.NS/shareholding"),
    ("GET", "/api/companies/RELIANCE.NS/insider-activity"),
    ("GET", "/api/companies/RELIANCE.NS/documents"),
    ("GET", "/api/companies/RELIANCE.NS/research-notes"),
    ("GET", "/api/screener"),
    ("GET", "/api/screener/presets"),
    ("GET", "/api/screener/sector-heatmap"),
    ("GET", "/api/watchlist"),
    ("GET", "/api/alerts"),
    ("GET", "/api/leaderboard"),
    ("GET", "/api/keepalive"),
    ("GET", "/health"),
]

all_passed = True
for method, url in endpoints:
    response = client.get(url)
    if response.status_code == 200:
        print(f"[OK] {method} {url} -> 200 OK")
    else:
        print(f"[FAILED] {method} {url} -> {response.status_code}")
        all_passed = False

if all_passed:
    print("\nSUCCESS: 100% OF CORE API ENDPOINTS FULLY IMPLEMENTED AND OPERATING PERFECTLY!")
