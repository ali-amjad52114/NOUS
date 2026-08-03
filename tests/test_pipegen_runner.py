from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integrations.rocketride_runner import RocketRideUnavailable, run_protocol
from kit.pipegen import compile_pipe, validate_pipe_structure


PROTO = {"id": "P-001", "name": "Invoices", "trigger_class": "incoming_invoice",
         "steps": [{"action": "archive", "params": {}}],
         "postcondition": "archived", "taught_by": "owner"}


class PipeAndRunnerTest(unittest.TestCase):
    def test_canonical_pipe_and_callback_base(self):
        pipe = compile_pipe(PROTO, "https://nous.example")
        self.assertEqual(validate_pipe_structure(pipe), [])
        self.assertEqual([c["provider"] for c in pipe["components"]],
                         ["webhook", "nous_protocol", "response_text"])
        config = pipe["components"][1]["config"]
        self.assertEqual(config["callback_base"], "https://nous.example")
        self.assertEqual(config["protocol_id"], "P-001")

    def test_fallback_is_explicit_and_labeled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p.pipe"
            path.write_text(json.dumps(compile_pipe(PROTO)), encoding="utf-8")
            with patch.dict(os.environ, {"ROCKETRIDE_MODE": "fallback"}, clear=False):
                result = run_protocol(str(path), {"event_id": "evt-1", "protocol_id": "P-001",
                    "trigger_class": "incoming_invoice", "inputs": {}},
                    fallback_dispatch=lambda _path, _payload: {"ok": True})
        self.assertTrue(result["ok"])
        self.assertTrue(result["trace_ref"].startswith("fallback://"))

    def test_strict_mode_does_not_fallback_without_credentials(self):
        called = False
        def fallback(_path, _payload):
            nonlocal called
            called = True
            return {"ok": True}
        with patch.dict(os.environ, {"ROCKETRIDE_MODE": "cloud",
                                     "ROCKETRIDE_APIKEY": ""}, clear=False):
            with self.assertRaises(RocketRideUnavailable):
                run_protocol("missing.pipe", {"event_id": "evt-1", "protocol_id": "P-001",
                    "trigger_class": "incoming_invoice", "inputs": {}},
                    fallback_dispatch=fallback)
        self.assertFalse(called)

    def test_local_sdk_path_sends_contract_without_requiring_key(self):
        calls = []

        class FakeClient:
            def __init__(self, **options):
                calls.append(("init", options))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def ping(self):
                calls.append(("ping",))

            async def validate(self, pipeline):
                calls.append(("validate", pipeline["version"]))
                return {"valid": True}

            async def use(self, **options):
                calls.append(("use", options["pipelineTraceLevel"]))
                return {"token": "task-123"}

            async def send(self, token, data, **_options):
                payload = json.loads(data)
                calls.append(("send", token, payload))
                return {"result": [json.dumps({"ok": True, "receipt_ids": ["X-001"]})]}

            async def terminate(self, token):
                calls.append(("terminate", token))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p.pipe"
            path.write_text(json.dumps(compile_pipe(PROTO)), encoding="utf-8")
            with patch.dict(os.environ, {"ROCKETRIDE_MODE": "local",
                                         "ROCKETRIDE_URI": "ws://cursor-runtime:5565"},
                            clear=False):
                os.environ.pop("ROCKETRIDE_APIKEY", None)
                with patch("rocketride.RocketRideClient", FakeClient):
                    result = run_protocol(str(path), {"event_id": "evt-1",
                        "protocol_id": "P-001", "trigger_class": "incoming_invoice",
                        "inputs": {}})
        self.assertTrue(result["ok"])
        self.assertEqual(result["trace_ref"], "rocketride://task/task-123")
        self.assertNotIn("auth", calls[0][1])
        sent = next(call for call in calls if call[0] == "send")[2]
        self.assertEqual(set(sent), {"run_id", "event_id", "protocol_id",
                                     "trigger_class", "inputs"})

    def test_strict_sdk_path_fails_closed_on_unstructured_output(self):
        class FakeClient:
            def __init__(self, **_options): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *_args): return None
            async def ping(self): pass
            async def validate(self, _pipeline): return {"valid": True}
            async def use(self, **_options): return {"token": "task-bad"}
            async def send(self, *_args, **_options): return {"text": "not the callback result"}
            async def terminate(self, _token): pass

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "p.pipe"
            path.write_text(json.dumps(compile_pipe(PROTO)), encoding="utf-8")
            with patch.dict(os.environ, {"ROCKETRIDE_MODE": "local"}, clear=False):
                os.environ.pop("ROCKETRIDE_APIKEY", None)
                with patch("rocketride.RocketRideClient", FakeClient):
                    result = run_protocol(str(path), {"event_id": "evt-1",
                        "protocol_id": "P-001", "trigger_class": "incoming_invoice",
                        "inputs": {}})
        self.assertFalse(result["ok"])
        self.assertIn("structured Nous callback result", result["error"])


if __name__ == "__main__":
    unittest.main()
