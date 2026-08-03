#!/usr/bin/env python3
"""Phase-0 SDK lifecycle test. Requires a real RocketRide runtime/key."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from rocketride import RocketRideClient

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "integrations" / "rocketride" / "smoke.pipe"


async def smoke(uri: str, apikey: str | None) -> dict:
    pipeline = json.loads(PIPE.read_text(encoding="utf-8"))
    token = None
    client_options = {"uri": uri}
    if apikey:
        client_options["auth"] = apikey
    async with RocketRideClient(**client_options) as client:
        await client.ping()
        validation = await client.validate(pipeline)
        if validation.get("valid") is False or validation.get("errors"):
            raise RuntimeError(f"validation failed: {validation}")
        used = await client.use(filepath=str(PIPE), pipelineTraceLevel="FLOW")
        token = used["token"]
        try:
            output = await client.send(token, "phase-0-ping",
                                       objinfo={"name": "phase-0.txt"},
                                       mimetype="text/plain")
            if not output:
                raise RuntimeError("RocketRide returned an empty response")
        finally:
            await client.terminate(token)
    return {"ok": True, "sdk": "rocketride==1.3.0", "uri": uri,
            "token": token, "validation": validation, "output": output,
            "ts": datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    uri = os.environ.get("ROCKETRIDE_URI", "ws://localhost:5565")
    apikey = os.environ.get("ROCKETRIDE_APIKEY")
    result = asyncio.run(smoke(uri, apikey))
    rendered = json.dumps(result, indent=2, default=str)
    print(rendered)
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
