"""Strict RocketRide SDK runner with an explicit rehearsal-only fallback."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Callable


class RocketRideUnavailable(RuntimeError):
    pass


def _validation_failed(result: object) -> bool:
    if not isinstance(result, dict):
        return False
    return result.get("valid") is False or bool(result.get("errors"))


async def _run_live(pipe_path: str, payload: dict, mode: str) -> dict:
    try:
        from rocketride import RocketRideClient
    except ImportError as exc:
        raise RocketRideUnavailable("install SDK: pip install rocketride==1.3.0") from exc

    uri = os.environ.get("ROCKETRIDE_URI")
    apikey = os.environ.get("ROCKETRIDE_APIKEY")
    if not uri:
        uri = "ws://localhost:5565" if mode == "local" else "https://api.rocketride.ai"
    if mode == "cloud" and not apikey:
        raise RocketRideUnavailable("ROCKETRIDE_APIKEY is required in cloud mode")

    pipeline = json.loads(Path(pipe_path).read_text(encoding="utf-8"))
    token = None
    client_options = {"uri": uri}
    if apikey:
        client_options["auth"] = apikey
    async with RocketRideClient(**client_options) as client:
        await client.ping()
        validation = await client.validate(pipeline)
        if _validation_failed(validation):
            raise RuntimeError(f"RocketRide validation failed: {validation}")
        used = await client.use(filepath=str(Path(pipe_path).resolve()),
                                pipelineTraceLevel="FLOW")
        token = used["token"]
        try:
            output = await client.send(token, json.dumps(payload),
                                       objinfo={"name": f"{payload['event_id']}.json"},
                                       mimetype="text/plain")
        finally:
            await client.terminate(token)
    ok = False
    callback_result = None
    error = "RocketRide response did not contain a structured Nous callback result"
    returned = output.get("result") if isinstance(output, dict) else None
    if isinstance(returned, list) and returned:
        try:
            callback_result = (json.loads(returned[0]) if isinstance(returned[0], str)
                               else returned[0])
            if isinstance(callback_result, dict) and isinstance(callback_result.get("ok"), bool):
                ok = callback_result["ok"]
                error = callback_result.get("error") if not ok else None
        except (TypeError, json.JSONDecodeError) as exc:
            error = f"invalid RocketRide callback JSON: {exc}"
    return {"run_id": payload["run_id"], "ok": ok, "output": output,
            "callback_result": callback_result, "error": error,
            "trace_ref": f"rocketride://task/{token}", "mode": mode}


def run_protocol(pipe_path: str, event_payload: dict, *,
                 fallback_dispatch: Callable[[str, dict], dict] | None = None) -> dict:
    """Run one protocol. Strict modes never silently fall back."""
    mode = os.environ.get("ROCKETRIDE_MODE", "fallback").lower()
    if mode not in {"local", "cloud", "fallback"}:
        raise ValueError("ROCKETRIDE_MODE must be local, cloud, or fallback")
    payload = {**event_payload}
    payload.setdefault("run_id", f"rr-{uuid.uuid4().hex[:16]}")
    required = ("run_id", "event_id", "protocol_id", "trigger_class", "inputs")
    missing = [key for key in required if payload.get(key) is None]
    if missing:
        raise ValueError(f"missing RocketRide payload fields: {missing}")
    if mode == "fallback":
        if fallback_dispatch is None:
            raise RocketRideUnavailable("fallback mode requires an explicit dispatcher")
        output = fallback_dispatch(pipe_path, payload)
        return {"run_id": payload["run_id"], "ok": bool(output.get("ok")),
                "output": output, "trace_ref": f"fallback://{payload['run_id']}",
                "mode": "fallback"}
    return asyncio.run(_run_live(pipe_path, payload, mode))
