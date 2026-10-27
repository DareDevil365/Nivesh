"""Compare collected packs with independently reviewed facts; never seed app answers."""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))


def evaluate(case, pack):
    from services.filing_reader import normalize_text
    from services.filing_sources import document_kind

    docs = pack.get("documents", [])
    names = {
        normalize_text(n["name"]).casefold().rstrip(".")
        for d in docs
        for n in d.get("relationships", [])
    }
    rows = [r for d in docs for r in d.get("financial_metrics", [])]
    evidence = normalize_text(
        " ".join(p["text"] for d in docs for p in d.get("passages", []))
    ).casefold()
    checks = []
    for name in case["counterparties"]:
        checks.append(
            {
                "check": "counterparty:" + name,
                "pass": normalize_text(name).casefold().rstrip(".") in names,
            }
        )
    for expected in case["metrics"]:
        matches = [
            r
            for r in rows
            if all(r[k] == expected[k] for k in ("basis", "period", "metric"))
            and math.isclose(
                r["value_cr"], expected["value_cr"], abs_tol=0.001, rel_tol=1e-7
            )
        ]
        checks.append(
            {
                "check": f"financial:{expected['basis']}:{expected['metric']}",
                "pass": bool(matches),
                "expected_value_cr": expected["value_cr"],
            }
        )
    for keyword in case["keywords"]:
        checks.append(
            {
                "check": "retrieved_evidence:" + keyword,
                "pass": keyword.casefold() in evidence,
            }
        )
    checks.append(
        {
            "check": "earnings_transcript",
            "pass": any(document_kind(d) == "transcript" for d in docs),
        }
    )
    checks.append(
        {
            "check": "exclude_newspaper_evidence",
            "pass": not any("newspaper" in d.get("title", "").lower() for d in docs),
        }
    )
    return {
        "documents": len(docs),
        "relationship_count": len(names),
        "passed": sum(c["pass"] for c in checks),
        "total": len(checks),
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--packs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    results = []
    for case in cases["cases"]:
        ticker = case["ticker"].split(".")[0]
        row = {"ticker": case["ticker"]}
        for phase in ("before", "after"):
            pack = json.loads(
                (args.packs / f"{ticker}-{phase}.json").read_text(encoding="utf-8")
            )
            if pack.get("ticker") != case["ticker"]:
                raise ValueError("Pack issuer does not match benchmark.")
            row[phase] = evaluate(case, pack)
        results.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "as_of": cases["as_of"],
                "limitations": "Coverage of selected independently reviewed facts, not a quality score or investment certification. No live AI generation is evaluated.",
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            [
                {
                    "ticker": row["ticker"],
                    "before": f"{row['before']['passed']}/{row['before']['total']}",
                    "after": f"{row['after']['passed']}/{row['after']['total']}",
                    "remaining": [
                        c["check"] for c in row["after"]["checks"] if not c["pass"]
                    ],
                }
                for row in results
            ],
            ensure_ascii=False,
        )
    )
    return (
        0
        if all(row["after"]["passed"] == row["after"]["total"] for row in results)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
