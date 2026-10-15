"""Deploy the reviewed bundle using existing Git credentials; never log secrets."""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "output/research/targeted-research-deployment.json"
BRANCH = "codex/targeted-news-research"
PR_TITLE = "Add targeted primary-source research across daily news editions"
PR_BODY = "Daily briefs previously summarised independently collected sources without following selected stories back to their underlying evidence. Add a shared bounded follow-up desk to the AI newsletter and world/India finance and general-news editions. It selects a few stories, searches for matching official documents, reads available excerpts, and displays source status, unresolved questions and what to watch. Related documents remain context, not certified corroboration.\n\nReuse the existing summary calls with paired story/context citation checks. Preserve accepted delivery IDs, private mailbox handling, Telegram-only delivery and the six-AM IST schedule. Offline input runs stay offline; unsupported or unavailable primary pages leave explicit gaps rather than invented verification.\n\nValidation covers relevance/version collisions, search-only snippets, missing/future dates, restricted pages, source pairing, email query privacy, scope isolation, offline behavior, bounded reads and transport limits. A live Hugging Face sample exercises original-page retrieval; hosted validation follows before deployment."



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("publish", "configure", "merge", "dispatch", "status", "enable", "disable"),
    )
    parser.add_argument("--repository", default="DareDevil365/Nivesh")
    parser.add_argument(
        "--send", action="store_true", help="Manual hosted run sends instead of previewing"
    )
    parser.add_argument("--check-mailbox", action="store_true", help="Verify read-only mailbox intake on a manual hosted run")
    args = parser.parse_args()
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repository):
        parser.error("Invalid repository")
    credential = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True,
        timeout=12,
        env={**os.environ, "GCM_INTERACTIVE": "never", "GIT_TERMINAL_PROMPT": "0"},
    )
    fields = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)
    token = fields.get("password")
    if not token:
        parser.error("Existing GitHub authentication is unavailable; authenticate Git first.")
    api = f"https://api.github.com/repos/{args.repository}"
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    with httpx.Client(
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
        trust_env=False,
    ) as client:

        def request(method, path, payload=None, allow404=False):
            response = client.request(method, api + path, json=payload)
            if allow404 and response.status_code == 404:
                return None
            if response.status_code not in (200, 201, 204):
                # Provider messages/bodies are deliberately excluded from logs.
                raise RuntimeError(
                    f"GitHub operation failed: {method} {path} ({response.status_code})"
                )
            return response.json() if response.content else {}

        def variable(name, value):
            present = request("GET", "/actions/variables/" + name, allow404=True)
            request(
                "PATCH" if present else "POST",
                "/actions/variables/" + name if present else "/actions/variables",
                {"name": name, "value": value},
            )

        if args.action == "publish":
            repo = request("GET", "")
            base = repo["default_branch"]
            remote = request("GET", "/git/ref/heads/" + BRANCH, allow404=True)
            if remote and remote["object"]["sha"] != state.get("head"):
                raise RuntimeError(
                    "The deployment branch changed or belongs to another run; refusing to overwrite it."
                )
            parent = (
                remote["object"]["sha"]
                if remote
                else request("GET", "/git/ref/heads/" + base)["object"]["sha"]
            )
            parent_commit = request("GET", "/git/commits/" + parent)
            manifest = json.loads((ROOT / "bundle_manifest.json").read_text(encoding="utf-8"))
            private = dotenv_values(ROOT / ".env")
            forbidden = [token]
            for name, value in private.items():
                if value and any(
                    part in name
                    for part in (
                        "KEY",
                        "PASSWORD",
                        "TOKEN",
                        "USER",
                        "EMAIL",
                        "CHAT_ID",
                        "PAIR_CODE",
                    )
                ):
                    forbidden.extend(piece for piece in value.split(",") if len(piece) >= 8)
            entries = []
            paths = [*manifest, "bundle_manifest.json"]
            for path in paths:
                data = (ROOT / path).read_bytes()
                content = data.decode("utf-8")
                if any(secret in content for secret in forbidden):
                    raise RuntimeError("Private configuration found in a publishable file.")
                if (
                    path in manifest
                    and hashlib.sha256(data).hexdigest() != manifest[path]["sha256"]
                ):
                    raise RuntimeError("Project changed after manifest build.")
                entries.append(
                    {
                        "path": "daily-brief/" + path,
                        "mode": "100644",
                        "type": "blob",
                        "content": content,
                    }
                )
            workflow = (ROOT / ".github/workflows/daily-news.yml").read_text(encoding="utf-8")
            if any(secret in workflow for secret in forbidden):
                raise RuntimeError("Private configuration found in workflow.")
            entries.append(
                {
                    "path": ".github/workflows/daily-news.yml",
                    "mode": "100644",
                    "type": "blob",
                    "content": workflow,
                }
            )
            previous = request("GET", "/git/trees/" + parent_commit["tree"]["sha"] + "?recursive=1")
            if previous.get("truncated"):
                raise RuntimeError("Repository tree was truncated; refusing incomplete migration.")
            removed = [
                entry["path"]
                for entry in previous["tree"]
                if entry["path"].startswith("news-bot/") and entry["type"] == "blob"
            ]
            entries.extend(
                {"path": path, "mode": "100644", "type": "blob", "sha": None} for path in removed
            )
            tree = request(
                "POST", "/git/trees", {"base_tree": parent_commit["tree"]["sha"], "tree": entries}
            )
            commit = request(
                "POST",
                "/git/commits",
                {
                    "message": PR_TITLE,
                    "tree": tree["sha"],
                    "parents": [parent],
                },
            )
            if remote:
                request(
                    "PATCH", "/git/refs/heads/" + BRANCH, {"sha": commit["sha"], "force": False}
                )
            else:
                request("POST", "/git/refs", {"ref": "refs/heads/" + BRANCH, "sha": commit["sha"]})
            state.update(head=commit["sha"], base=base)
            if not state.get("pr"):
                pr = request(
                    "POST",
                    "/pulls",
                    {
                        "title": PR_TITLE,
                        "head": BRANCH,
                        "base": base,
                        "body": PR_BODY,
                    },
                )
                state.update(pr=pr["number"], url=pr["html_url"])
            request(
                "PATCH",
                f"/pulls/{state['pr']}",
                {
                    "title": PR_TITLE,
                    "body": PR_BODY,
                },
            )
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
            print(
                json.dumps(
                    {"pull_request": state["url"], "files": len(paths), "head": state["head"]}
                )
            )
        elif args.action == "configure":
            from nacl import public

            values = dotenv_values(ROOT / ".env")
            values["GEMINI_API_KEYS"] = (
                values.get("GEMINI_API_KEYS") or values.get("GEMINI_API_KEY") or ""
            )
            channel = values.get("NEWS_DELIVERY", "telegram")
            if channel not in ("email", "telegram"):
                raise RuntimeError("Invalid NEWS_DELIVERY setting.")
            variable("NEWS_BOT_ENABLED", "false")
            variable("NEWS_DELIVERY", channel)
            variable(
                "NEWS_LEARNING_START_DATE", values.get("NEWS_LEARNING_START_DATE") or "2026-10-15"
            )
            variable(
                "NEWS_FINANCE_START_DATE", values.get("NEWS_FINANCE_START_DATE") or "2026-10-15"
            )
            variable("AI_NEWSLETTER_ENABLED", values.get("AI_NEWSLETTER_ENABLED") or "true")
            variable("NEWS_RESEARCH_ENABLED", values.get("NEWS_RESEARCH_ENABLED") or "true")
            variable("NEWSLETTER_IMAP_ENABLED", values.get("NEWSLETTER_IMAP_ENABLED") or "false")
            public_key = request("GET", "/actions/secrets/public-key")
            box = public.SealedBox(public.PublicKey(base64.b64decode(public_key["key"])))
            configured, missing = [], []
            names = [
                "GEMINI_API_KEYS",
                "GEMINI_KEY_PROJECTS",
                "NEWSLETTER_IMAP_USER",
                "NEWSLETTER_IMAP_PASSWORD",
                "NEWSLETTER_ALLOWED_SENDERS",
            ] + (
                ["NEWS_TELEGRAM_BOT_TOKEN", "NEWS_TELEGRAM_CHAT_ID"]
                if channel == "telegram"
                else ["NEWS_SMTP_USER", "NEWS_SMTP_PASSWORD", "NEWS_EMAIL_TO"]
            )
            for name in names:
                value = values.get(name) or ""
                if not value and name not in (
                    "GEMINI_KEY_PROJECTS",
                    "NEWSLETTER_ALLOWED_SENDERS",
                    "NEWSLETTER_IMAP_USER",
                    "NEWSLETTER_IMAP_PASSWORD",
                ):
                    missing.append(name)
                    continue
                request(
                    "PUT",
                    "/actions/secrets/" + name,
                    {
                        "key_id": public_key["key_id"],
                        "encrypted_value": base64.b64encode(box.encrypt(value.encode())).decode(),
                    },
                )
                configured.append(name)
            variable("NEWS_BOT_ENABLED", "false")
            print(
                json.dumps(
                    {
                        "configured_secret_names": configured,
                        "missing": missing,
                        "schedule_enabled": False,
                    }
                )
            )
        elif args.action == "merge":
            if not state.get("pr"):
                raise RuntimeError("No deployment pull request is recorded.")
            runs = request("GET", "/actions/runs?event=pull_request&head_sha=" + state["head"])[
                "workflow_runs"
            ]
            passed = any(
                run["name"] == "Daily Brief" and run["conclusion"] == "success" for run in runs
            )
            if not passed:
                raise RuntimeError(
                    "Hosted pull-request verification has not passed; refusing to merge."
                )
            merged = request(
                "PUT",
                f"/pulls/{state['pr']}/merge",
                {"sha": state["head"], "merge_method": "squash"},
            )
            print(json.dumps({"merged": merged.get("merged"), "sha": merged.get("sha")}))
        elif args.action == "dispatch":
            repo = request("GET", "")
            request(
                "POST",
                "/actions/workflows/daily-news.yml/dispatches",
                {"ref": repo["default_branch"], "inputs": {"dry_run": not args.send, "check_mailbox": args.check_mailbox}},
            )
            print(json.dumps({"hosted_run_dispatched": True, "dry_run": not args.send}))
        elif args.action == "disable":
            variable("NEWS_BOT_ENABLED", "false")
            print(json.dumps({"schedule_enabled": False}))
        elif args.action == "enable":
            private = dotenv_values(ROOT / ".env")
            required = (
                ("NEWS_TELEGRAM_BOT_TOKEN", "NEWS_TELEGRAM_CHAT_ID")
                if private.get("NEWS_DELIVERY") == "telegram"
                else ("NEWS_SMTP_PASSWORD",)
            )
            if any(not private.get(name) for name in required):
                raise RuntimeError(
                    "Delivery credentials/pairing are missing; do not enable an unconfigured schedule."
                )
            variable("NEWS_BOT_ENABLED", "true")
            print(json.dumps({"schedule_enabled": True, "time": "06:00 IST"}))
        else:
            path = "/actions/runs?per_page=8" if state.get("head") else "/actions/runs?per_page=5"
            runs = request("GET", path)["workflow_runs"]
            print(
                json.dumps(
                    {
                        "runs": [
                            {
                                key: run.get(key)
                                for key in (
                                    "id",
                                    "name",
                                    "event",
                                    "status",
                                    "conclusion",
                                    "html_url",
                                    "head_sha",
                                )
                            }
                            for run in runs
                            if run["name"] == "Daily Brief"
                        ]
                    }
                )
            )


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, httpx.HTTPError, subprocess.SubprocessError) as error:
        print(str(error))
        raise SystemExit(1) from None
