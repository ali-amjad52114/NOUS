"""Publish NOUS evidence through LaserData's official quickstart producer."""
from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kit.feed import STORY, classify


HOST = os.environ.get(
    "LASERDATA_HOST",
    "starter-1d50iz-xh9ok2vqasmgk.us-central1.gcp.laserdata.cloud",
)
CERTIFICATE = Path(
    os.environ.get("LASERDATA_CERT", "~/Downloads/laserdata.crt")
).expanduser()
PROJECT = Path(__file__).resolve().parent.parent
STATE = PROJECT / "state"
IMAGE = "ghcr.io/laserdata/quickstart:latest"


def _receipts() -> list[dict]:
    actions = [
        ("evt-2", "book", "brain"),
        ("evt-2", "send_message", "brain"),
        ("evt-3", "forward", "human"),
        ("evt-3", "label", "human"),
        ("evt-3", "archive", "human"),
        ("evt-5", "forward", "brain"),
        ("evt-5", "label", "brain"),
        ("evt-5", "archive", "brain"),
        ("evt-6", "forward", "brain"),
        ("evt-6", "label", "brain"),
        ("evt-6", "archive", "brain"),
    ]
    return [
        {
            "id": f"X-{index:03d}",
            "event_id": event_id,
            "action": action,
            "actor": actor,
            "ok": True,
            "ts": time.time(),
        }
        for index, (event_id, action, actor) in enumerate(actions, start=1)
    ]


def _publish(password: str, topic: str, payload_path: Path, count: int) -> int:
    command = ["docker"]
    colima_socket = Path("~/.colima/default/docker.sock").expanduser()
    if not os.environ.get("DOCKER_HOST") and colima_socket.exists():
        command.extend(["-H", f"unix://{colima_socket}"])
    command.extend([
        "run",
        "--rm",
        "-v",
        f"{CERTIFICATE}:/cert/laserdata.crt:ro",
        "-v",
        f"{payload_path}:/data.json:ro",
        IMAGE,
        "/producer",
        HOST,
        "-u",
        "root",
        "-p",
        password,
        "--tls-cert",
        "/cert/laserdata.crt",
        "--stream",
        "nous",
        "--topic",
        topic,
        "--messages-count",
        str(count),
        "--file",
        "/data.json",
        "--flush-each-message",
    ])
    return subprocess.run(command, check=False).returncode


def main() -> int:
    if not CERTIFICATE.is_file():
        print(f"LaserData certificate not found: {CERTIFICATE}")
        return 1

    password = getpass.getpass("LaserData password (hidden): ")
    if not password:
        print("No password provided.")
        return 1

    STATE.mkdir(exist_ok=True)
    events = [
        {**event, "trigger_class": classify(event), "ts": time.time()}
        for event in STORY
    ]
    receipts = _receipts()
    events_path = STATE / "laserdata_life_events.json"
    receipts_path = STATE / "laserdata_receipts.json"
    events_path.write_text(json.dumps(events))
    receipts_path.write_text(json.dumps(receipts))

    try:
        if _publish(password, "life-events", events_path, len(events)) != 0:
            return 1
        if _publish(password, "receipts", receipts_path, len(receipts)) != 0:
            return 1
        print("LaserData evidence ready: nous/life-events=6, nous/receipts=11")
        return 0
    finally:
        password = ""


if __name__ == "__main__":
    raise SystemExit(main())
