"""THE ROCKETRIDE MONEY MOVE: every learned protocol compiles into a .pipe.

The brain doesn't just remember skills — it emits them as RocketRide
pipelines. Skills-as-pipelines is the "builds the most with RocketRide" play:
  * each learned protocol => pipes/P-XXX.pipe (portable JSON, git-committable)
  * run them on the local engine (docker, :5565) AND deploy one to
    RocketRide Cloud with the promo code
  * recreate one on the VS Code canvas with a RocketRide mentor so the
    canonical node schema matches — then show the observability trace live
  * tell the CEO: "your engine is the compilation target of our brain"
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

PIPES = Path(__file__).resolve().parent.parent / "pipes"


def callback_base() -> str:
    return os.environ.get("NOUS_CALLBACK_BASE", "http://127.0.0.1:7200").rstrip("/")


def compile_pipe(proto: dict, base_url: str | None = None) -> dict:
    """Compile to RocketRide's canonical v1 component graph.

    `nous_protocol` is a deterministic custom RocketRide filter shipped under
    integrations/rocketride/nodes. It owns precheck -> ordered steps -> verify.
    """
    base = (base_url or callback_base()).rstrip("/")
    pid = proto["id"]
    postcondition = proto.get("postcondition", "")
    if not isinstance(postcondition, str):
        postcondition = json.dumps(postcondition, separators=(",", ":"), sort_keys=True)
    project_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://nous.local/protocol/{pid}"))
    return {
        "components": [
            {"id": "webhook_1", "provider": "webhook",
             "config": {"hideForm": True, "mode": "Source", "parameters": {},
                        "type": "webhook"},
             "ui": {"position": {"x": 20, "y": 160}}},
            {"id": "nous_protocol_1", "provider": "nous_protocol",
             "config": {"type": "nous_protocol", "callback_base": base,
                        "protocol_id": pid, "trigger_class": proto["trigger_class"],
                        "steps": proto.get("steps", []),
                        "postcondition": postcondition},
             "input": [{"lane": "text", "from": "webhook_1"}],
             "ui": {"position": {"x": 240, "y": 160}}},
            {"id": "response_text_1", "provider": "response_text",
             "config": {"laneName": "result"},
             "input": [{"lane": "text", "from": "nous_protocol_1"}],
             "ui": {"position": {"x": 460, "y": 160}}},
        ],
        "project_id": project_id,
        "description": f"Nous protocol {pid} ({proto['trigger_class']})",
        "viewport": {"x": 0, "y": 0, "zoom": 1},
        "version": 1,
    }


def validate_pipe_structure(pipe: dict) -> list[str]:
    """Fast offline guard; the live runner additionally calls SDK validate()."""
    errors = []
    if pipe.get("version") != 1 or not isinstance(pipe.get("components"), list):
        errors.append("expected RocketRide v1 components")
    providers = [c.get("provider") for c in pipe.get("components", [])]
    if providers != ["webhook", "nous_protocol", "response_text"]:
        errors.append(f"unexpected provider chain: {providers}")
    ids = {c.get("id") for c in pipe.get("components", [])}
    for component in pipe.get("components", []):
        for edge in component.get("input", []):
            if edge.get("from") not in ids:
                errors.append(f"unknown input source {edge.get('from')}")
    cfg = next((c.get("config", {}) for c in pipe.get("components", [])
                if c.get("provider") == "nous_protocol"), {})
    if not cfg.get("callback_base", "").startswith(("http://", "https://")):
        errors.append("callback_base must be http(s)")
    if not cfg.get("protocol_id") or not isinstance(cfg.get("steps"), list):
        errors.append("protocol id and steps are required")
    return errors


def emit_pipe(proto: dict, execute_url: str | None = None) -> str:
    """Compile a learned protocol into a validated RocketRide pipeline file."""
    base = execute_url.rsplit("/actions/", 1)[0] if execute_url and "/actions/" in execute_url else None
    pipe = compile_pipe(proto, base)
    errors = validate_pipe_structure(pipe)
    if errors:
        raise ValueError("invalid RocketRide pipe: " + "; ".join(errors))

    PIPES.mkdir(exist_ok=True)
    path = PIPES / f"{proto['id']}.pipe"
    path.write_text(json.dumps(pipe, indent=2), encoding="utf-8")
    return str(path)
