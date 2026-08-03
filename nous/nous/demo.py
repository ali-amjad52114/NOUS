#!/usr/bin/env python3
"""Full demo arc, headless. `python3 demo.py` — ends with ALL CHECKS PASSED."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kit import feed  # noqa: E402
from kit.brain import Brain  # noqa: E402

brain = Brain()
brain.store.reset()
S = feed.STORY

print("=" * 70)
print("BEAT 1 — THE PROMISE. Sam's news arrives; you reply; the brain acts.")
print("=" * 70)
assert brain.ingest(S[0]) == "remembered"          # Sam's diagnosis
assert brain.ingest(S[1]) == "proposed"            # your promise -> commitment + slot
c = brain.store.open_commitments()[0]
assert c["status"] == "proposed" and c["person"] == "Sam"
r = brain.approve_commitment(c["id"])              # Guild HITL approval
assert r == "booked"
assert brain.store.g["commitments"][c["id"]]["booked_slot"]

print()
print("=" * 70)
print("BEAT 2 — LEARNS YOUR MOVES. First invoice ever: it watches you.")
print("=" * 70)
assert brain.ingest(S[2]) == "watching"
brain.human_action("forward", {"to": "accounting@myfirm.com"})
brain.human_action("label", {"name": "invoices"})
brain.human_action("archive", {})
proto = brain.human_done()
assert not proto["approved"]

print()
print("=" * 70)
print("BEAT 3 — NOISE ignored · REFUSAL before approval · then autonomous.")
print("=" * 70)
assert brain.ingest(S[3]) == "ignored"                      # newsletter
assert brain.ingest(S[4]) == "refused_pending_approval"     # 2nd vendor, unarmed
assert brain.approve(proto["id"]) == ["acted"]              # arm -> queue drains
assert brain.ingest(S[5]) == "acted"                        # 3rd vendor, autonomous

print()
print(brain.store.describe())
print()
print(brain.inbox.scoreboard())

# persistence: a brand-new brain instance still knows everything
b2 = Brain()
assert b2.store.find_protocol("incoming_invoice", "new invoice due")["protocol"]["approved"]
assert any(c["status"] == "booked" for c in b2.store.g["commitments"].values())
print("\npersistence: new brain instance still holds the armed protocol AND the booked promise ✓")
print("\nALL CHECKS PASSED — demo is stage-ready")
