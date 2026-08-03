"""Replay NOUS life events from LaserData/Apache Iggy offset 0."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.request

from apache_iggy import IggyClient, PollingStrategy


async def replay(post_url: str | None) -> None:
    connection_string = os.environ.get("LASERDATA_URL")
    if not connection_string:
        raise SystemExit("Set LASERDATA_URL to the Iggy connection string first.")

    client = IggyClient.from_connection_string(connection_string)
    await client.connect()
    messages = await client.poll_messages(
        stream=os.environ.get("LASERDATA_STREAM", "nous"),
        topic="life-events",
        partition_id=0,
        polling_strategy=PollingStrategy.First(),
        count=100,
        auto_commit=False,
    )

    for message in messages:
        event = json.loads(message.payload())
        print(f"offset={message.offset()} id={event.get('id')} class={event.get('trigger_class')}")
        if post_url:
            request = urllib.request.Request(
                post_url,
                data=json.dumps(event).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                print(f"  reposted → HTTP {response.status}")

    print(f"replayed {len(messages)} life event(s) from the beginning")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--post",
        nargs="?",
        const="http://127.0.0.1:7200/events",
        help="also POST each replayed event to NOUS (optional endpoint)",
    )
    args = parser.parse_args()
    asyncio.run(replay(args.post))
