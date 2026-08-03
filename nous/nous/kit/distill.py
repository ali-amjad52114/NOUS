"""Distiller + Safety Critic — the Guild.ai agent roles.

At the venue these two run as Guild specialists (Distiller agent + Critic
agent, published via `guild agent init/save`). The deterministic versions here
keep the demo unkillable; the Nebius hook upgrades the prose when a key is set.
"""
from __future__ import annotations

import json
import os
import urllib.request

ALLOWED_ACTIONS = {"forward", "label", "archive", "reply"}

DISTILL_PROMPT = """You watched a person handle an item in their life stream.
Compile their handling into a GENERALIZED protocol (JSON only):
{"name": "...", "trigger_class": "<given>", "signature_example": "<given>",
 "preconditions": ["typed, checkable conditions"],
 "steps": [{"action": "forward|label|archive|reply", "params": {...}}],
 "postcondition": "verifiable end state", "risk": "low|medium|high"}
Parameterize — never hardcode this one item's values. Allowed actions only."""


def distill(evt: dict, watched: list[dict]) -> dict:
    """Deterministic distiller: generalize the watched session into a protocol."""
    steps = []
    for w in watched:
        if w["action"] in ALLOWED_ACTIONS and not any(s["action"] == w["action"] for s in steps):
            params = dict(w.get("params", {}))
            steps.append({"action": w["action"], "params": params})
    return {
        "name": f"Handle {evt['trigger_class'].replace('_', ' ')}",
        "trigger_class": evt["trigger_class"],
        "signature_example": evt.get("subject", ""),
        "preconditions": [
            "event trigger class matches this protocol's class",
            "every step action is on the allowlist",
            "forwarding target is a known, configured address",
            "protocol has been approved by its owner",
        ],
        "steps": steps,
        "postcondition": "item is forwarded and archived; receipt recorded",
        "risk": "low",
    }


def critique(proto: dict) -> dict:
    """Safety Critic: try to reject the protocol before a human ever sees it."""
    notes, ok = [], True
    bad = [s["action"] for s in proto.get("steps", []) if s["action"] not in ALLOWED_ACTIONS]
    if bad:
        ok, _ = False, notes.append(f"REJECT: non-allowlisted actions {bad}")
    else:
        notes.append("all steps within the action allowlist ✓")
    if not proto.get("steps"):
        ok, _ = False, notes.append("REJECT: no steps")
    if not proto.get("preconditions") or not proto.get("postcondition"):
        ok, _ = False, notes.append("REJECT: missing preconditions/postcondition")
    else:
        notes.append(f"{len(proto['preconditions'])} typed preconditions + postcondition ✓")
    if proto.get("risk", "high") != "low":
        notes.append(f"note: risk={proto.get('risk')} — require re-approval per use")
    notes.append("recommend: HUMAN APPROVAL required before this protocol is armed"
                 if ok else "recommend: DO NOT ARM")
    return {"ok": ok, "notes": notes}


def llm_upgrade(prompt: str, payload: str) -> str | None:
    """Optional Nebius call (OpenAI-compatible). Returns None on any failure —
    the deterministic path above is always the safety net."""
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        return None
    try:
        req = urllib.request.Request(
            os.environ.get("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1").rstrip("/")
            + "/chat/completions",
            data=json.dumps({"model": os.environ.get("NEBIUS_MODEL", ""),
                             "messages": [{"role": "system", "content": prompt},
                                          {"role": "user", "content": payload}],
                             "temperature": 0.2}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception:
        return None
