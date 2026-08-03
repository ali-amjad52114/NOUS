"""Simulated inbox + allowlisted action executor (the brain's hands).

Every action is allowlisted and receipted. RocketRide is the execution path
at the venue: the generated .pipe calls POST /actions/execute on this server —
so the engine, not the app, drives the motion (see pipegen.py).
"""
from __future__ import annotations

import time
import threading

from .laserdata import publish_event

ALLOWED = {"forward", "label", "archive", "reply", "book", "send_message"}


class Inbox:
    def __init__(self):
        self.items: dict[str, dict] = {}      # event_id -> item state
        self.receipts: list[dict] = []
        self.human_actions = 0
        self.brain_actions = 0
        self._lock = threading.Lock()

    def add(self, evt: dict):
        self.items[evt["id"]] = {"evt": evt, "labels": [], "archived": False,
                                 "forwarded_to": None, "replied": None}

    def execute(self, event_id: str, action: str, params: dict, actor: str,
                *, run_id: str | None = None, step_id: str | None = None,
                protocol_id: str | None = None) -> str:
        if action not in ALLOWED:
            raise ValueError(f"action {action!r} not in allowlist {sorted(ALLOWED)}")
        item = self.items.get(event_id)
        if not item:
            raise ValueError(f"unknown item {event_id}")
        if action == "forward":
            item["forwarded_to"] = params.get("to")
            result = f"forwarded to {params.get('to')}"
        elif action == "label":
            item["labels"].append(params.get("name"))
            result = f"labeled '{params.get('name')}'"
        elif action == "archive":
            item["archived"] = True
            result = "archived"
        elif action == "book":
            item["booked"] = params.get("slot")
            result = f"calendar hold created: {params.get('slot')} with {params.get('with_person')}"
        elif action == "send_message":
            item["sent"] = params.get("text", "")[:100]
            result = f"message sent to {params.get('to')}: \"{params.get('text', '')[:60]}...\""
        else:
            item["replied"] = params.get("text", "")[:80]
            result = "replied"
        if actor == "brain":
            self.brain_actions += 1
        else:
            self.human_actions += 1
        receipt = {"id": f"X-{len(self.receipts) + 1:03d}", "event_id": event_id,
                   "action": action, "params": params, "actor": actor,
                   "result": result, "ts": time.time(), "run_id": run_id,
                   "step_id": step_id, "protocol_id": protocol_id}
        self.receipts.append(receipt)
        publish_event(receipt, topic="receipts")
        return result

    def execute_once(self, event_id: str, action: str, params: dict, *,
                     run_id: str, step_id: str, protocol_id: str) -> dict:
        """Execute one RocketRide step exactly once, even across engine retries."""
        if not run_id or not step_id:
            raise ValueError("run_id and step_id are required")
        with self._lock:
            duplicate = next((r for r in self.receipts
                              if r.get("run_id") == run_id and r.get("step_id") == step_id), None)
            if duplicate:
                return {"duplicate": True, "receipt": duplicate,
                        "result": duplicate["result"]}
            result = self.execute(event_id, action, params, "brain", run_id=run_id,
                                  step_id=step_id, protocol_id=protocol_id)
            return {"duplicate": False, "receipt": self.receipts[-1], "result": result}

    def verify_handled(self, event_id: str) -> bool:
        """Postcondition: invoice items are handled iff forwarded AND archived."""
        item = self.items.get(event_id, {})
        return bool(item.get("forwarded_to")) and item.get("archived", False)

    def scoreboard(self) -> str:
        return (f"actions — you: {self.human_actions} · brain: {self.brain_actions} "
                f"· receipts: {len(self.receipts)}")
