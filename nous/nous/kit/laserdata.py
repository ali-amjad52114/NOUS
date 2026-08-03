"""Failure-safe LaserData publisher backed by the Apache Iggy Python SDK."""
from __future__ import annotations

import asyncio
import json
import os
import socket
from urllib.parse import urlparse


STREAM = os.environ.get("LASERDATA_STREAM", "nous")
CONNECTION_STRING = os.environ.get("LASERDATA_URL", "")
PUBLISH_TIMEOUT = float(os.environ.get("LASERDATA_TIMEOUT", "2"))


async def _publish(payload: dict, topic: str) -> None:
    from apache_iggy import IggyClient, SendMessage

    client = IggyClient.from_connection_string(CONNECTION_STRING)
    await client.connect()

    # Iggy's create calls are intentionally not idempotent. Existing resources
    # are the expected case after the first event, so those errors are ignored.
    try:
        await client.create_stream(name=STREAM)
    except Exception:
        pass
    try:
        await client.create_topic(
            stream=STREAM,
            name=topic,
            partitions_count=1,
            replication_factor=1,
        )
    except Exception:
        pass

    await client.send_messages(
        stream=STREAM,
        topic=topic,
        partitioning=0,
        messages=[SendMessage(json.dumps(payload, separators=(",", ":")))],
    )


def publish_event(payload: dict, topic: str) -> bool:
    """Publish within two seconds; never let streaming failure stop the demo."""
    if not CONNECTION_STRING:
        return False
    try:
        endpoint = urlparse(CONNECTION_STRING)
        if endpoint.hostname and endpoint.port:
            with socket.create_connection((endpoint.hostname, endpoint.port), timeout=0.25):
                pass
        asyncio.run(asyncio.wait_for(_publish(payload, topic), timeout=PUBLISH_TIMEOUT))
        event_id = payload.get("id", "event")
        print(f"   📡 LaserData {STREAM}/{topic} ← {event_id}")
        return True
    except Exception as exc:
        detail = str(exc).replace(CONNECTION_STRING, "<connection-redacted>")
        if endpoint.password:
            detail = detail.replace(endpoint.password, "<password-redacted>")
        suffix = f": {detail}" if detail else ""
        print(
            f"   ⚠ LaserData unavailable ({type(exc).__name__}{suffix}); "
            "continuing locally"
        )
        return False
