"""Runtime adapter for Guild API-trigger sessions with a labeled fallback.

Live mode uses two independently configured API triggers. Each trigger key is
bound to its published Guild agent. Guild's documented workspace sessions API
returns the session record; the adapter polls that session and validates the
typed output again before Nous trusts it.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

from kit import distill as local
from .schemas import (ALLOWED_ACTIONS, SchemaError, validate_critic_output,
                      validate_distiller_input, validate_protocol)


class GuildIntegrationError(RuntimeError):
    pass


def _safe_event(event: dict) -> dict:
    fields = {k: event.get(k) for k in ("subject", "from", "person") if event.get(k) is not None}
    return {"id": event["id"], "trigger_class": event["trigger_class"], "fields": fields}


def _distiller_input(event: dict, receipts: list[dict], owner_id: str) -> dict:
    value = {
        "source_event": _safe_event(event),
        "watched_receipts": [
            {"order": i, "action": r["action"], "params": dict(r.get("params", {}))}
            for i, r in enumerate(receipts, 1)
        ],
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "owner_id": owner_id,
    }
    return validate_distiller_input(value)


def _basic(credentials: str) -> str:
    return "Basic " + base64.b64encode(credentials.encode()).decode()


def _request(method: str, url: str, credentials: str, payload: dict | None,
             timeout: float) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": _basic(credentials), "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GuildIntegrationError(f"Guild request failed for {url}: {exc}") from exc


def _session_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("session_id", "id"):
            if isinstance(value.get(key), str) and value[key]:
                return value[key]
        for child in value.values():
            found = _session_id(child)
            if found:
                return found
    return None


def _candidate_objects(value: Any):
    if isinstance(value, dict):
        yield value
        for key in ("agent_output", "output", "result", "data", "content", "payload"):
            if key in value:
                yield from _candidate_objects(value[key])
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from _candidate_objects(child)
    elif isinstance(value, list):
        for child in reversed(value):
            yield from _candidate_objects(child)
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return
        yield from _candidate_objects(parsed)


def _extract_output(records: list[Any], validator) -> dict | None:
    for record in reversed(records):
        for candidate in _candidate_objects(record):
            try:
                return validator(candidate)
            except SchemaError:
                continue
    return None


def _live_agent(kind: str, agent_input: dict, validator) -> tuple[dict, dict]:
    base = os.environ.get("GUILD_BASE_URL", "https://app.guild.ai").rstrip("/")
    owner, workspace = os.environ.get("GUILD_WORKSPACE_OWNER"), os.environ.get("GUILD_WORKSPACE_NAME")
    credentials = os.environ.get(f"GUILD_{kind.upper()}_CREDENTIALS")
    if not owner or not workspace or not credentials:
        raise GuildIntegrationError(
            f"live Guild {kind} requires GUILD_WORKSPACE_OWNER, GUILD_WORKSPACE_NAME, "
            f"and GUILD_{kind.upper()}_CREDENTIALS")
    timeout = float(os.environ.get("GUILD_TIMEOUT_SECONDS", "45"))
    endpoint = f"{base}/api/workspaces/{owner}/{workspace}/sessions"
    started = _request("POST", endpoint, credentials,
                       {"session_type": "api_trigger", "agent_input": agent_input}, timeout)
    sid = _session_id(started)
    if not sid:
        raise GuildIntegrationError(f"Guild {kind} response did not contain a session ID")
    deadline, records = time.monotonic() + timeout, [started]
    status_url = f"{base}/api/sessions/{sid}"
    while time.monotonic() < deadline:
        status = _request("GET", status_url, credentials, None, min(timeout, 10))
        records.append(status)
        output = _extract_output(records, validator)
        if output:
            break
        state = str(status.get("status") or status.get("state") or "").lower()
        if state in {"failed", "error", "cancelled", "canceled"}:
            raise GuildIntegrationError(f"Guild {kind} session {sid} ended with {state}")
        time.sleep(0.5)
    else:
        raise GuildIntegrationError(f"Guild {kind} session {sid} timed out")
    events = _request("GET", f"{status_url}/events?limit=100", credentials, None, min(timeout, 10))
    records.append(events)
    output = _extract_output(records, validator)
    if not output:
        raise GuildIntegrationError(f"Guild {kind} session {sid} returned no schema-valid output")
    version = (status.get("agent_version_id") or status.get("version_id") or
               os.environ.get(f"GUILD_{kind.upper()}_VERSION"))
    if not version:
        raise GuildIntegrationError(f"Guild {kind} session {sid} did not expose an agent version")
    agent_id = status.get("agent_id") or os.environ.get(f"GUILD_{kind.upper()}_AGENT_ID")
    if not agent_id:
        raise GuildIntegrationError(f"Guild {kind} session {sid} did not expose an agent ID")
    return output, {"session": sid, "version": version, "agent": agent_id}


def _review_protocol(event: dict, receipts: list[dict], owner_id: str) -> dict:
    """Run Distiller then Critic and return only schema-validated judgment."""
    mode = os.environ.get("GUILD_MODE", "fallback").lower()
    if mode not in {"live", "fallback"}:
        raise GuildIntegrationError("GUILD_MODE must be live or fallback")
    distilled_input = _distiller_input(event, receipts, owner_id)
    if mode == "live":
        protocol, distiller_meta = _live_agent("distiller", distilled_input, validate_protocol)
        critic_input = {"protocol": protocol, "policy": {
            "allowed_actions": sorted(ALLOWED_ACTIONS), "human_final_authority": True,
            "reject_hardcoded_one_off_values": True, "require_approval_precondition": True,
            "require_verifiable_postcondition": True,
        }}
        review, critic_meta = _live_agent("critic", critic_input, validate_critic_output)
    else:
        protocol = validate_protocol(local.distill(event, receipts))
        review = validate_critic_output(local.critique(protocol))
        distiller_meta = {"session": f"fallback-distiller-{uuid.uuid4()}",
                          "version": "deterministic-distiller-v1", "agent": "local-nous-distiller"}
        critic_meta = {"session": f"fallback-critic-{uuid.uuid4()}",
                       "version": "deterministic-critic-v1", "agent": "local-nous-critic"}
    provenance = {
        "guild_mode": mode,
        "guild_schema_validated": True,
        "guild_distiller_session": distiller_meta["session"],
        "guild_critic_session": critic_meta["session"],
        "guild_agent_ids": {"distiller": distiller_meta["agent"],
                            "critic": critic_meta["agent"]},
        "guild_agent_versions": {"distiller": distiller_meta["version"],
                                 "critic": critic_meta["version"]},
        "critic_verdict": review["verdict"],
        "critic_findings": review["findings"],
        "critic_residual_risk": review["residual_risk"],
        "critic_checks": review["checks"],
    }
    return {"protocol": protocol, "review": review, "provenance": provenance}


def review_protocol(event: dict, receipts: list[dict], owner_id: str) -> dict:
    """Fail closed and normalize every contract failure for the product layer."""
    try:
        return _review_protocol(event, receipts, owner_id)
    except SchemaError as exc:
        raise GuildIntegrationError(f"Guild output failed schema validation: {exc}") from exc
