"""Distiller + Safety Critic — the Guild.ai agent roles.

At the venue these two run as Guild specialists (Distiller agent + Critic
agent, published via `guild agent init/save`). The deterministic versions here
keep the demo unkillable; the Nebius hook upgrades the prose when a key is set.
"""
from __future__ import annotations

import json
import os
import urllib.request

ALLOWED_ACTIONS = {"forward", "label", "archive", "reply", "book", "send_message"}

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
            {"field": "event.trigger_class", "operator": "equals",
             "value": evt["trigger_class"]},
            {"field": "protocol.steps[].action", "operator": "subset_of",
             "value": sorted(ALLOWED_ACTIONS)},
            {"field": "protocol.approved", "operator": "equals", "value": True},
        ],
        "steps": steps,
        "postcondition": {"checks": [
            {"kind": "receipt_exists", "action": step["action"]} for step in steps
        ]},
        "risk": "low",
    }


def critique(proto: dict) -> dict:
    """Safety Critic: try to reject the protocol before a human ever sees it."""
    steps = proto.get("steps") if isinstance(proto.get("steps"), list) else []
    preconditions = proto.get("preconditions") if isinstance(proto.get("preconditions"), list) else []
    post = proto.get("postcondition") if isinstance(proto.get("postcondition"), dict) else {}
    actions_ok = bool(steps) and all(s.get("action") in ALLOWED_ACTIONS for s in steps)
    parameterized = all(
        not any(key in str(value).lower() for key in ("vendor", "acme", "globex"))
        for step in steps for value in step.get("params", {}).values()
    )
    approval = any(p.get("field") == "protocol.approved" and p.get("value") is True
                   for p in preconditions if isinstance(p, dict))
    checks = post.get("checks") if isinstance(post.get("checks"), list) else []
    post_ok = bool(checks) and all(c.get("kind") == "receipt_exists" and
                                   c.get("action") in ALLOWED_ACTIONS for c in checks)
    normalized = {"allowlisted_actions": actions_ok, "parameterized_inputs": parameterized,
                  "approval_precondition": approval, "verifiable_postcondition": post_ok}
    messages = {
        "allowlisted_actions": "one or more steps are empty or not allowlisted",
        "parameterized_inputs": "protocol contains a hardcoded one-off entity",
        "approval_precondition": "owner approval is not a typed precondition",
        "verifiable_postcondition": "postcondition is not expressed as receipt checks",
    }
    findings = [{"number": i, "code": key.upper(), "message": messages[key],
                 "severity": "critical"}
                for i, key in enumerate((k for k, passed in normalized.items() if not passed), 1)]
    ok = all(normalized.values())
    return {"verdict": "APPROVE_ELIGIBLE" if ok else "REJECT", "findings": findings,
            "residual_risk": ("Low after explicit owner approval; execution remains allowlisted and receipted."
                              if ok else "Unsafe until every critical finding is corrected."),
            "checks": normalized}


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
