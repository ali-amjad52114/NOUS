#!/usr/bin/env python3
"""Drive the real server path so RocketRide callbacks reach the same Brain."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kit.feed import STORY


def request(base: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base.rstrip("/") + path, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return {"status": response.status, "body": json.loads(response.read())}
    except urllib.error.HTTPError as exc:
        detail = json.loads(exc.read())
        raise RuntimeError(f"{path} failed ({exc.code}): {detail}") from exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:7200")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    story, calls = STORY, []

    def post(path, body):
        result = request(args.base, path, body)
        calls.append({"path": path, "request": body, "response": result})
        return result["body"]

    assert post("/events", story[0])["status"] == "remembered"
    assert post("/events", story[1])["status"] == "proposed"
    assert post("/approve-commitment", {"commitment_id": "C-001"})["status"] == "booked"
    assert post("/events", story[2])["status"] == "watching"
    post("/watch/action", {"action": "forward", "params": {"to": "accounting@myfirm.com"}})
    post("/watch/action", {"action": "label", "params": {"name": "invoices"}})
    post("/watch/action", {"action": "archive", "params": {}})
    protocol = post("/watch/done", {})["protocol"]
    assert post("/events", story[4])["status"] == "refused_pending_approval"
    acted = post("/approve", {"protocol_id": protocol["id"]})["acted_on"]
    assert acted == ["acted"]
    assert post("/events", story[5])["status"] == "acted"
    state = request(args.base, "/state")
    evidence = {"ok": True, "ts": datetime.now(timezone.utc).isoformat(),
                "protocol_id": protocol["id"], "calls": calls, "state": state}
    rendered = json.dumps(evidence, indent=2)
    print(rendered)
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
