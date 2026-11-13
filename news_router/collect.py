"""Pull official OpenAI Codex stable releases and OpenAI incident updates."""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from .core import load_feed, parse_time, save_feed, utc_now


def get_json(url: str, *, gh: bool = False) -> dict | list:
    headers = {"User-Agent": "openai-codex-news-router/0.1", "Accept": "application/json"}
    if gh and os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f'Bearer {os.environ["GITHUB_TOKEN"]}'
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    with urlopen(Request(url, headers=headers), timeout=20) as resp:
        return json.load(resp)


def topic_for(text: str) -> list[str]:
    t = text.lower()
    mapping = {"images": ("image", "bild", "sunburst", "flare", "gif"),
               "connectors": ("connector", "microsoft", "outlook", "gmail", "mcp"),
               "work": ("work", "dots", "agent", "sites", "spaces", "workspace"),
               "api": ("api", "billing", "payment", "platform"),
               "windows": ("windows", "desktop"),
               "security": ("security", "vulnerability", "cyber", "privacy"),
               "codex": ("codex", "cli", "code"),
               "chatgpt": ("chatgpt", "conversation", "chat"),
               "models": ("model", "gpt-", "reasoning")}
    selected = [k for k, words in mapping.items() if any(word in t for word in words)]
    return selected or ["general"]


def incidents() -> list[dict]:
    # Statuspage API exposes official public incidents with updated_at/status.
    result = get_json("https://status.openai.com/api/v2/incidents.json")
    output = []
    for x in result.get("incidents", []):
        updated = x.get("updated_at") or x.get("created_at")
        if not updated or parse_time(updated) < utc_now() - timedelta(days=10):
            continue
        raw_status = x.get("status", "")
        status = "resolved" if raw_status in ("resolved", "postmortem", "completed") else "monitoring" if raw_status == "monitoring" else "active"
        updates = x.get("incident_updates") or []
        body = next((u.get("body", "") for u in updates if u.get("body")), "Weitere Details im offiziellen Störungsbericht.")
        name = x.get("name") or "OpenAI-Störung"
        output.append({"id": "incident-" + x["id"], "title": name[:200],
                       "summary": body[:1000], "source_url": f'https://status.openai.com/incidents/{x["id"]}',
                       "updated_at": updated, "topics": topic_for(name + " " + body), "kind": "incident", "status": status})
    return output


def releases() -> list[dict]:
    data = get_json("https://api.github.com/repos/openai/codex/releases?per_page=15", gh=True)
    output = []
    for x in data:
        if x.get("draft") or x.get("prerelease"):
            continue
        updated = x.get("published_at")
        if not updated or parse_time(updated) < utc_now() - timedelta(days=10):
            continue
        tag = x.get("tag_name", "")
        if any(s in tag.lower() for s in ("-alpha", "-beta", "-rc", "nightly")):
            continue
        link = x.get("html_url", "")
        if not link.startswith("https://github.com/openai/codex/releases/"):
            continue
        output.append({"id": "codex-" + tag.replace("/", "-"), "title": (x.get("name") or tag)[:200],
                       "summary": (x.get("body") or "Offizielles Codex-Release.")[:1000], "source_url": link,
                       "updated_at": updated, "topics": ["codex", "windows"], "kind": "release", "status": "published"})
    return output


def main() -> None:
    p = argparse.ArgumentParser(description="Official OpenAI change collector")
    p.add_argument("--feed", default="feed.json")
    args = p.parse_args()
    file = Path(args.feed)
    events = load_feed(file) if file.exists() else []
    failed = []
    for name, fn in (("incidents", incidents), ("releases", releases)):
        try:
            events.extend(fn())
        except Exception as e:
            failed.append(f"{name}: {e}")
    if len(failed) == 2:
        raise SystemExit("Beide offiziellen Quellen nicht erreichbar: " + "; ".join(failed))
    if failed:
        print("WARNUNG (Teilausfall): " + "; ".join(failed))
    save_feed(file, events)
    print(f"Feed aktualisiert: {len(load_feed(file))} Meldungen")


if __name__ == "__main__":
    main()
