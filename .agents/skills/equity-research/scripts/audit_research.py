"""Audit a collected issuer pack, optionally re-downloading original quoted pages."""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker")
    parser.add_argument(
        "--pack", type=Path, help="Audit an existing JSON pack without network access."
    )
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--verify-originals", action="store_true")
    parser.add_argument(
        "--source-limit",
        type=int,
        choices=range(1, 7),
        default=6,
        help="Maximum original sources to recheck (default: all six retained sources).",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    from services.research_audit import audit_research, verify_originals

    if args.pack:
        if args.verify_originals:
            parser.error(
                "Original verification needs live issuer identity; omit --pack."
            )
        state = json.loads(args.pack.read_text(encoding="utf-8"))
        if state.get("ticker", "").upper() != args.ticker.upper():
            parser.error("Pack ticker does not match requested issuer.")
        result = audit_research(state)
    else:
        with httpx.Client(base_url=args.server, timeout=90) as client:
            endpoint = "/api/companies/" + quote(args.ticker, safe="")
            responses = [
                client.get(endpoint + suffix)
                for suffix in ("", "/research-workflow", "/financials")
            ]
            for response in responses:
                response.raise_for_status()
            profile, state, financials = [response.json() for response in responses]
        result = audit_research(state, financials)
        if args.verify_originals:
            result["checks"].extend(
                verify_originals(profile, state, limit=args.source_limit)
            )
            result["original_source_limit"] = args.source_limit
            if any(check["status"] == "fail" for check in result["checks"]):
                result["status"] = "fail"
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        counts = {
            status: sum(c["status"] == status for c in result["checks"])
            for status in ("pass", "warning", "fail")
        }
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "counts": counts,
                    "output": str(args.output),
                }
            )
        )
    else:
        print(text)
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
