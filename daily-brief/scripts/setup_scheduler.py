"""Configure only Daily Brief jobs on cron-job.org; do not print request secrets."""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "output/research/external-scheduler.json"
REPO = "DareDevil365/Nivesh"
TARGET = f"https://api.github.com/repos/{REPO}/actions/workflows/daily-news.yml/dispatches"


def job_payload(token, hour, minute, title):
    return {
        "title": title,
        "url": TARGET,
        "enabled": True,
        "saveResponses": False,
        "requestMethod": 1,
        "requestTimeout": 30,
        "redirectSuccess": False,
        "schedule": {
            "timezone": "Asia/Kolkata",
            "expiresAt": 0,
            "hours": [hour],
            "minutes": [minute],
            "mdays": [-1],
            "months": [-1],
            "wdays": [-1],
        },
        "extendedData": {
            "headers": {
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            "body": json.dumps(
                {
                    "ref": "main",
                    "inputs": {"dry_run": False, "check_mailbox": False, "hold_until_six": True},
                }
            ),
        },
        "notification": {
            "onFailure": True,
            "onFailureCount": 1,
            "onDisable": True,
            "onSuccess": False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "configure", "status"])
    args = parser.parse_args()
    if args.action == "plan":
        print(
            json.dumps(
                {
                    "primary": "05:40 Asia/Kolkata; prepare and hold until 06:00",
                    "backup": "06:05 Asia/Kolkata; accepted claims skip repeats",
                    "required_private_fields": ["NEWS_CRON_API_KEY", "NEWS_CRON_GITHUB_TOKEN"],
                    "github_permissions": "Selected repository Actions: Read and write",
                    "sends_secrets_to": "cron-job.org stores the repository-limited dispatch token in its request headers",
                }
            )
        )
        return
    values = dotenv_values(ROOT / ".env")
    api_key = values.get("NEWS_CRON_API_KEY") or ""
    token = values.get("NEWS_CRON_GITHUB_TOKEN") or ""
    if not api_key or not token:
        raise RuntimeError(
            "Add NEWS_CRON_API_KEY and NEWS_CRON_GITHUB_TOKEN privately to Daily Brief/.env."
        )
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    with httpx.Client(timeout=20, trust_env=False) as client:

        def request(method, path, payload=None):
            r = client.request(
                method,
                "https://api.cron-job.org" + path,
                headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code != 200:
                raise RuntimeError(f"External scheduler operation failed ({r.status_code}).")
            return r.json()

        if args.action == "configure":
            # Verify the limited credential on a non-sending dispatch before installing jobs.
            r = client.post(
                TARGET,
                headers={
                    "Authorization": "Bearer " + token,
                    "Accept": "application/vnd.github+json",
                },
                json={
                    "ref": "main",
                    "inputs": {"dry_run": True, "check_mailbox": False, "hold_until_six": False},
                },
            )
            if r.status_code != 204:
                raise RuntimeError(
                    f"Repository-limited workflow dispatch check failed ({r.status_code})."
                )
            jobs = request("GET", "/jobs")
            if jobs.get("someFailed"):
                raise RuntimeError(
                    "Scheduler job inventory is incomplete; refusing duplicate creation."
                )
            for name, hour, minute in [
                ("Daily Brief — Morning", 5, 40),
                ("Daily Brief — Backup", 6, 5),
            ]:
                matches = [j for j in jobs["jobs"] if j["title"] == name and j["url"] == TARGET]
                if len(matches) > 1:
                    raise RuntimeError(
                        "Multiple matching Daily Brief jobs exist; resolve the duplicates first."
                    )
                payload = job_payload(token, hour, minute, name)
                if matches:
                    identifier = matches[0]["jobId"]
                    request("PATCH", f"/jobs/{identifier}", {"job": payload})
                else:
                    identifier = request("PUT", "/jobs", {"job": payload})["jobId"]
                    time.sleep(1.1)
                state[name] = identifier
                STATE.parent.mkdir(parents=True, exist_ok=True)
                STATE.write_text(json.dumps(state), encoding="utf-8")
        results = []
        for name, identifier in state.items():
            job = request("GET", f"/jobs/{identifier}")["jobDetails"]
            results.append(
                {
                    "name": name,
                    "enabled": job["enabled"],
                    "schedule": job["schedule"],
                    "nextExecution": job.get("nextExecution"),
                    "lastStatus": job.get("lastStatus"),
                }
            )
        print(json.dumps({"jobs": results, "github_cron_can_remain_as_late_backup": True}))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, httpx.HTTPError) as error:
        print(
            str(error)
            if isinstance(error, RuntimeError)
            else "External scheduler network request failed.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
