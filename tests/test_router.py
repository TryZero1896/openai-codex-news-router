import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from news_router.core import trusted, validate, match, digest, save_feed, load_feed, notice
from news_router.collect import topic_for

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)
def event(**changes):
    item = {"id": "incident-test", "title": "ChatGPT Image generation errors", "summary": "Elevated error rate.",
            "source_url": "https://status.openai.com/incidents/abc123", "updated_at": NOW.isoformat(),
            "topics": ["images", "chatgpt"], "kind": "incident", "status": "active"}
    item.update(changes)
    return item

class RouterTests(unittest.TestCase):
    def test_route(self):
        self.assertTrue(match(event(), ["images"], NOW))
        self.assertFalse(match(event(), ["codex"], NOW))
        self.assertFalse(match(event(updated_at=(NOW-timedelta(days=12)).isoformat()), ["images"], NOW))
    def test_resolved_expiry(self):
        e = event(status="resolved", updated_at=(NOW-timedelta(hours=40)).isoformat())
        self.assertFalse(match(e, ["images"], NOW))
    def test_new_status_redeliver(self):
        self.assertNotEqual(digest(event()), digest(event(status="resolved")))
    def test_trusted_domains(self):
        self.assertTrue(trusted("https://github.com/openai/codex/releases/tag/rust-v1"))
        self.assertFalse(trusted("https://github.com/attacker/codex/releases/tag/rust-v1"))
        self.assertFalse(trusted("https://status.openai.com.evil.org/incidents/x"))
        self.assertFalse(trusted("http://status.openai.com/incidents/x"))
    def test_feed_merge(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "feed.json"
            save_feed(p, [event(), event(status="resolved", updated_at=(NOW+timedelta(hours=1)).isoformat())])
            xs = load_feed(p)
            self.assertEqual(len(xs), 1)
            self.assertEqual(xs[0]["status"], "resolved")
    def test_injection_is_context(self):
        n = notice(event())
        self.assertIn("KEIN Arbeitsauftrag", n)
        self.assertIn("status.openai.com", n)
    def test_topic_map(self):
        self.assertIn("images", topic_for("Image generation failing"))
        self.assertIn("connectors", topic_for("Outlook connector unavailable"))

if __name__ == "__main__":
    unittest.main()
