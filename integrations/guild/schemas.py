"""Strict, dependency-free contracts at the Nous/Guild trust boundary."""
from __future__ import annotations

from typing import Any

ALLOWED_ACTIONS = {"forward", "label", "archive", "reply", "book", "send_message"}
VERDICTS = {"APPROVE_ELIGIBLE", "REJECT"}


class SchemaError(ValueError):
    pass


def _dict(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise SchemaError(f"{name} must be an object")
    return value


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{name} must be a non-empty string")
    return value


def validate_distiller_input(value: Any) -> dict:
    data = _dict(value, "distiller input")
    event = _dict(data.get("source_event"), "source_event")
    _nonempty(event.get("id"), "source_event.id")
    _nonempty(event.get("trigger_class"), "source_event.trigger_class")
    _dict(event.get("fields"), "source_event.fields")
    receipts = data.get("watched_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise SchemaError("watched_receipts must be a non-empty array")
    for index, receipt in enumerate(receipts, 1):
        receipt = _dict(receipt, f"watched_receipts[{index}]")
        if receipt.get("order") != index:
            raise SchemaError("watched_receipts must have contiguous 1-based order")
        _nonempty(receipt.get("action"), f"watched_receipts[{index}].action")
        _dict(receipt.get("params"), f"watched_receipts[{index}].params")
    actions = data.get("allowed_actions")
    if not isinstance(actions, list) or set(actions) != ALLOWED_ACTIONS:
        raise SchemaError("allowed_actions must contain the complete Nous allowlist")
    _nonempty(data.get("owner_id"), "owner_id")
    return data


def validate_protocol(value: Any) -> dict:
    proto = _dict(value, "protocol")
    _nonempty(proto.get("name"), "protocol.name")
    _nonempty(proto.get("trigger_class"), "protocol.trigger_class")
    _nonempty(proto.get("signature_example"), "protocol.signature_example")
    preconditions = proto.get("preconditions")
    if not isinstance(preconditions, list) or not preconditions:
        raise SchemaError("protocol.preconditions must be a non-empty array")
    for index, check in enumerate(preconditions):
        check = _dict(check, f"protocol.preconditions[{index}]")
        _nonempty(check.get("field"), f"protocol.preconditions[{index}].field")
        _nonempty(check.get("operator"), f"protocol.preconditions[{index}].operator")
        if "value" not in check:
            raise SchemaError(f"protocol.preconditions[{index}].value is required")
    steps = proto.get("steps")
    if not isinstance(steps, list) or not steps:
        raise SchemaError("protocol.steps must be a non-empty array")
    for index, step in enumerate(steps):
        step = _dict(step, f"protocol.steps[{index}]")
        action = _nonempty(step.get("action"), f"protocol.steps[{index}].action")
        if action not in ALLOWED_ACTIONS:
            raise SchemaError(f"protocol.steps[{index}].action is not allowlisted")
        _dict(step.get("params"), f"protocol.steps[{index}].params")
    post = _dict(proto.get("postcondition"), "protocol.postcondition")
    checks = post.get("checks")
    if not isinstance(checks, list) or not checks:
        raise SchemaError("protocol.postcondition.checks must be a non-empty array")
    for index, check in enumerate(checks):
        check = _dict(check, f"protocol.postcondition.checks[{index}]")
        if check.get("kind") != "receipt_exists":
            raise SchemaError("postcondition checks must be receipt_exists checks")
        if check.get("action") not in ALLOWED_ACTIONS:
            raise SchemaError("postcondition check action is not allowlisted")
    if proto.get("risk") not in {"low", "medium", "high"}:
        raise SchemaError("protocol.risk must be low, medium, or high")
    return proto


def validate_critic_output(value: Any) -> dict:
    review = _dict(value, "critic output")
    if review.get("verdict") not in VERDICTS:
        raise SchemaError("critic verdict must be APPROVE_ELIGIBLE or REJECT")
    findings = review.get("findings")
    if not isinstance(findings, list):
        raise SchemaError("critic findings must be an array")
    for index, finding in enumerate(findings, 1):
        finding = _dict(finding, f"critic findings[{index}]")
        if finding.get("number") != index:
            raise SchemaError("critic findings must be contiguously numbered")
        _nonempty(finding.get("code"), f"critic findings[{index}].code")
        _nonempty(finding.get("message"), f"critic findings[{index}].message")
        if finding.get("severity") not in {"info", "warning", "critical"}:
            raise SchemaError("critic finding severity is invalid")
    _nonempty(review.get("residual_risk"), "critic residual_risk")
    checks = _dict(review.get("checks"), "critic checks")
    required = {"allowlisted_actions", "parameterized_inputs", "approval_precondition",
                "verifiable_postcondition"}
    if set(checks) != required or not all(isinstance(v, bool) for v in checks.values()):
        raise SchemaError("critic checks must contain the four normalized boolean checks")
    if review["verdict"] == "APPROVE_ELIGIBLE" and not all(checks.values()):
        raise SchemaError("approve-eligible verdict requires every normalized check to pass")
    return review
