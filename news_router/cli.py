"""Local Windows dispatcher; defaults to dry-run for safety."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from .core import load_feed, match, digest, notice, parse_time, validate, save_feed
from .rpc import AppServer


def feed_from_location(location: str) -> list[dict]:
    if location.startswith("https://"):
        p = urlparse(location)
        if not ((p.hostname == "raw.githubusercontent.com" and p.path == "/TryZero1896/openai-codex-news-router/main/feed.json") or
                (p.hostname == "github.com" and p.path == "/TryZero1896/openai-codex-news-router/raw/refs/heads/main/feed.json")):
            raise ValueError("Es sind nur unveränderte Feed-URLs des News-Router-Repositorys erlaubt")
        with urlopen(Request(location, headers={"User-Agent": "openai-codex-news-router/0.1"}), timeout=15) as r:
            raw = json.load(r)
        return [validate(e) for e in raw["events"]]
    return load_feed(Path(location))


def run(config_path: Path, apply: bool = False) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    feed = feed_from_location(config["feed"])
    state_path = config_path.parent / "delivery-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    candidates = []
    for entry in config["threads"]:
        thread_id, topics = entry["thread_id"], entry["topics"]
        sent = set(state.get(thread_id, []))
        for event in feed:
            if match(event, topics) and digest(event) not in sent:
                candidates.append((thread_id, event))
    if not candidates:
        print("Keine neuen relevanten Meldungen")
        return
    if not apply:
        for thread_id, event in candidates:
            print(f'DRY RUN -> {thread_id}: {event["title"]} [{event["status"]}]')
        print("Keine Änderungen. Für Injektion --apply verwenden (zuerst an Test-Thread prüfen).")
        return
    # Separate app-server process; UI visibility in the Codex desktop app is NOT guaranteed.
    with AppServer(config.get("codex_executable", "codex")) as rpc:
        for thread_id, event in candidates:
            try:
                # Inspect status first; never inject into an active thread on this app-server.
                metadata = rpc.call("thread/read", {"threadId": thread_id})
                status_type = (metadata.get("thread", {}).get("status") or {}).get("type")
                if status_type not in ("idle", "notLoaded"):
                    print(f'SKIP -> {thread_id}: Thread-Status {status_type!r}; keine Injektion')
                    continue
                # First load the persisted thread. Failure must never create a new chat.
                resumed = rpc.call("thread/resume", {"threadId": thread_id, "excludeTurns": True})
                live_status = (resumed.get("thread", {}).get("status") or {}).get("type")
                if live_status == "active":
                    print(f'SKIP -> {thread_id}: währenddessen aktiv geworden')
                    continue
                rpc.call("thread/inject_items", {"threadId": thread_id, "items": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": notice(event)}]}]})
                state.setdefault(thread_id, []).append(digest(event))
                state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print(f'INJEKTION -> {thread_id}: {event["title"]}')
            except Exception as exc:
                print(f'FEHLER -> {thread_id}: {event["title"]}: {exc}')


def main() -> None:
    p = argparse.ArgumentParser(description="OpenAI Codex news router")
    sub = p.add_subparsers(dest="cmd", required=True)
    dispatch = sub.add_parser("dispatch", help="Windows: prüfe betroffene Chats")
    dispatch.add_argument("--config", default="windows/config.json")
    dispatch.add_argument("--apply", action="store_true", help="Wirklich in gespeicherte Threads injizieren")
    ls = sub.add_parser("threads", help="Lokale Codex-Threads und IDs anzeigen")
    ls.add_argument("--codex", default="codex")
    publish = sub.add_parser("publish", help="Publiziere eine kuratierte Meldung in den Feed")
    publish.add_argument("--feed", default="feed.json")
    publish.add_argument("--file", required=True, help="JSON-Meldung im Event-Schema")
    args = p.parse_args()
    if args.cmd == "dispatch":
        run(Path(args.config), apply=args.apply)
    elif args.cmd == "threads":
        with AppServer(args.codex) as rpc:
            cursor = None
            for _ in range(3):
                params = {"limit": 50}
                if cursor:
                    params["cursor"] = cursor
                result = rpc.call("thread/list", params)
                for th in result.get("data", []):
                    print(f'{th.get("id", "?")} | {th.get("name") or th.get("preview", "")[:100]} | {th.get("cwd", "")}')
                cursor = result.get("nextCursor")
                if not cursor:
                    break
    else:
        f = Path(args.feed)
        event = validate(json.loads(Path(args.file).read_text(encoding="utf-8")))
        existing = load_feed(f) if f.exists() else []
        save_feed(f, existing + [event])
        print(f'Kuratierte Meldung veröffentlicht: {event["id"]}')

if __name__ == "__main__":
    main()
