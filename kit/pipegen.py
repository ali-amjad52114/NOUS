"""Compile learned protocols into RocketRide pipelines.

The brain does not just remember skills, it emits them as executable
RocketRide pipeline definitions:

  * every approved protocol becomes pipes/<id>.pipe, portable JSON that is
    committed alongside the code
  * the same file runs on the local RocketRide engine and deploys unchanged
    to RocketRide Cloud
  * every step calls back into the brain's allowlisted /actions/* endpoints,
    so the engine drives the motion and the brain keeps the receipts
"""
from __future__ import annotations

import json
from pathlib import Path

PIPES = Path(__file__).resolve().parent.parent / "pipes"


def emit_pipe(proto: dict, execute_url: str = "http://127.0.0.1:7200/actions/execute") -> str:
    """Compile a learned protocol into a RocketRide pipeline definition."""
    nodes = [{"id": "trigger", "type": "webhook", "path": f"/protocol/{proto['id']}",
              "comment": f"fires when an event of class '{proto['trigger_class']}' arrives"},
             {"id": "preconditions", "type": "http", "method": "POST",
              "url": execute_url.replace("/execute", "/preconditions"),
              "comment": "verify every typed precondition before touching anything"}]
    lanes = [["trigger", "preconditions"]]
    prev = "preconditions"
    for i, step in enumerate(proto.get("steps", []), 1):
        nid = f"step{i}_{step['action']}"
        nodes.append({"id": nid, "type": "http", "method": "POST", "url": execute_url,
                      "body": {"action": step["action"], "params": step.get("params", {}),
                               "protocol": proto["id"]}})
        lanes.append([prev, nid])
        prev = nid
    nodes.append({"id": "verify", "type": "http", "method": "POST",
                  "url": execute_url.replace("/execute", "/verify"),
                  "comment": proto.get("postcondition", "")})
    lanes.append([prev, "verify"])

    pipe = {"_comment": f"Auto-compiled by the personal brain from protocol {proto['id']} "
                        f"('{proto.get('name')}'), taught by {proto.get('taught_by')}. "
                        "Finalize node schema on the RocketRide VS Code canvas.",
            "name": f"brain-{proto['id'].lower()}",
            "version": 1,
            "source": {"type": "webhook", "path": f"/protocol/{proto['id']}"},
            "nodes": nodes, "lanes": lanes}

    PIPES.mkdir(exist_ok=True)
    path = PIPES / f"{proto['id']}.pipe"
    path.write_text(json.dumps(pipe, indent=2))
    return str(path)
