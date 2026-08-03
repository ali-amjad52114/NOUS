"""Simulated life stream (Gmail + Slack + calendar) — the LaserData layer.

Deterministic replay = controllable demo; never demo live Google auth on
stage. Swap `publish` for the LaserData SDK/REST call (topic "life.events").
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state"
EVENTS_LOG = STATE / "events.jsonl"

# Your calendar's free slots (days_out lets the brain honor the 15-day window)
FREE_SLOTS = [
    {"slot": "Saturday Aug 15, 2:00–6:00 PM", "days_out": 12},
    {"slot": "Sunday Aug 16, 10:00 AM–1:00 PM", "days_out": 13},
]

# The demo storyline.
STORY = [
    # -- the heart of the demo -------------------------------------------
    {"id": "evt-1", "type": "message_in", "channel": "gmail", "from": "sam.k@gmail.com",
     "person": "Sam", "subject": "some news",
     "body": "Hey man. Got my diagnosis this week — it's cancer. Starting chemo at the end of the month. Weird few days."},
    {"id": "evt-2", "type": "message_out", "channel": "gmail", "to": "sam.k@gmail.com",
     "person": "Sam", "subject": "re: some news",
     "body": "Sam, I'm so sorry. Whatever you need. I'm coming to see you soon, I promise."},
    # -- the mechanism generalizes: learn-once protocols ------------------
    {"id": "evt-3", "type": "message_in", "channel": "gmail", "from": "billing@acmedesign.co",
     "person": "Acme Design", "subject": "Invoice #4417 — due Aug 17",
     "body": "Please find attached invoice for $850.", "attachment": "invoice_4417.pdf"},
    {"id": "evt-4", "type": "message_in", "channel": "slack", "from": "newsletter@technews.io",
     "person": "TechNews", "subject": "Your Monday briefing",
     "body": "Top stories in AI this week..."},
    {"id": "evt-5", "type": "message_in", "channel": "gmail", "from": "invoices@cloudhost.com",
     "person": "CloudHost", "subject": "CloudHost invoice CH-2231 for July",
     "body": "Amount due: $120. Invoice attached.", "attachment": "CH-2231.pdf"},
    {"id": "evt-6", "type": "message_in", "channel": "gmail", "from": "accounts@metroutilities.com",
     "person": "Metro Utilities", "subject": "Metro Utilities — invoice 88213",
     "body": "Your monthly invoice of $96 is attached.", "attachment": "88213.pdf"},
]

PROMISE_RE = re.compile(
    r"i('|’)?m coming to see you|i('|’)?ll (come )?(visit|see you|call|stop by)"
    r"|let'?s catch up|i promise", re.I)


def classify(evt: dict) -> str:
    text = f"{evt.get('subject', '')} {evt.get('body', '')}".lower()
    if evt.get("type") == "message_out" and PROMISE_RE.search(evt.get("body", "")):
        return "promise_made"
    if evt.get("type") == "message_in" and any(
            w in text for w in ("diagnosis", "chemo", "cancer", "hospital", "surgery")):
        return "important_personal"
    if "invoice" in text and (evt.get("attachment") or "due" in text):
        return "incoming_invoice"
    return "fyi_noise"


def publish(evt: dict) -> dict:
    """Persist + (venue) forward to LaserData. Returns the enriched event."""
    evt = {**evt, "ts": time.time(), "trigger_class": classify(evt)}
    STATE.mkdir(exist_ok=True)
    with EVENTS_LOG.open("a") as f:
        f.write(json.dumps(evt) + "\n")
    # VENUE TODO: laser.stream("brain").topic("life-events").publish().json(evt)
    return evt
