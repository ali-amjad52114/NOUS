#!/usr/bin/env python3
"""Minimal LaserData publish smoke test using LASERDATA_URL from .env."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env(ROOT / ".env")
    url = os.environ.get("LASERDATA_URL", "")
    if not url:
        print("LASERDATA_URL missing. Run: python integrations/laserdata_find_credentials.py")
        return 1

    from kit.laserdata import publish_event

    payload = {
        "id": f"smoke-{int(time.time())}",
        "type": "smoke_test",
        "channel": "laserdata",
        "subject": "Nous LaserData smoke",
        "body": "hello from Nous smoke test",
        "ts": time.time(),
        "trigger_class": "fyi_noise",
    }
    ok = publish_event(payload, topic="life-events")
    print("SMOKE_PASS" if ok else "SMOKE_FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
