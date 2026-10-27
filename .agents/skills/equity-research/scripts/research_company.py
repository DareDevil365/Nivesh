"""Collect public issuer evidence through the same service used by the app."""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker")
    parser.add_argument("--source-url", action="append", default=[])
    parser.add_argument("--context-url", action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Maximum seconds waiting for background collection.",
    )
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:8000",
        help="Reuse a running backend; collect locally if it is unavailable.",
    )
    args = parser.parse_args()
    if len(args.source_url) > 3:
        parser.error("Use at most three source URLs.")
    if len(args.context_url) > 3 or args.timeout < 1:
        parser.error("Use at most three context URLs and a positive timeout.")
    with httpx.Client(base_url=args.server, timeout=60) as client:
        try:
            use_server = client.get("/health", timeout=2).is_success
        except httpx.HTTPError:
            use_server = False
        if use_server:
            endpoint = f"/api/companies/{quote(args.ticker, safe='')}/research-workflow"
            response = (
                client.post(
                    endpoint,
                    json={
                        "source_urls": args.source_url,
                        "context_urls": args.context_url,
                    },
                )
                if args.force or args.source_url or args.context_url
                else client.get(endpoint)
            )
            response.raise_for_status()
            state = response.json()

            def read_state():
                response = client.get(endpoint)
                response.raise_for_status()
                return response.json()
        else:
            from services.data_fetcher import get_company_profile
            from services.research_workflow import cached_research, start_research

            profile = get_company_profile(args.ticker)
            state = start_research(
                profile,
                args.source_url,
                force=args.force or bool(args.source_url or args.context_url),
                context_urls=args.context_url,
            )

            def read_state():
                return cached_research(profile["ticker"])

        previous = None
        deadline = time.monotonic() + args.timeout
        while state["status"] in {"queued", "running"}:
            if time.monotonic() >= deadline:
                print(
                    "Timed out waiting; backend collection may still be running. Check the workflow status.",
                    file=sys.stderr,
                )
                return 2
            if state.get("progress") != previous:
                print(
                    state.get("progress", "Collecting reports..."),
                    file=sys.stderr,
                    flush=True,
                )
                previous = state.get("progress")
            time.sleep(2)
            state = read_state()
    text = json.dumps(state, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(
            f"Saved {len(state['documents'])} documents and {state['relationship_count']} relationships to {args.output}"
        )
    else:
        print(text)
    print(
        f"Collection status: {state['status']}. Coverage gaps require review; this is not a completed investment analysis.",
        file=sys.stderr,
    )
    return (
        1 if state["status"] in {"failed", "interrupted", "complete_with_gaps"} else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
