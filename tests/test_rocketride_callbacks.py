from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import server
from kit.brain import Brain
from kit.memory import LocalStore


EVENT = {"id": "evt-test", "from": "vendor@example.com", "subject": "Invoice 42",
         "body": "Please pay", "trigger_class": "incoming_invoice", "ts": 1}
STEPS = [{"action": "forward", "params": {"to": "accounting@example.com"}},
         {"action": "label", "params": {"name": "invoices"}},
         {"action": "archive", "params": {}}]


class CallbackAPITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        brain = Brain()
        brain.store = LocalStore(Path(self.temp.name) / "memory.json")
        brain.inbox.add(EVENT)
        brain.store.remember_event(EVENT)
        proto = brain.store.save_protocol({"name": "Invoices",
            "trigger_class": "incoming_invoice", "steps": STEPS,
            "preconditions": ["armed"], "postcondition": "forwarded, labeled, archived",
            "risk": "low"}, EVENT["id"], "owner")
        self.pid = proto["id"]
        server.brain = brain
        self.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.temp.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def payload(self, **changes):
        value = {"run_id": "rr-test", "event_id": EVENT["id"],
                 "protocol_id": self.pid, "trigger_class": "incoming_invoice",
                 "inputs": {}, "planned_actions": [s["action"] for s in STEPS]}
        value.update(changes)
        return value

    def test_happy_path_verify_and_duplicate_step(self):
        server.brain.store.approve(self.pid, "owner")
        code, pre = self.post("/actions/preconditions", self.payload())
        self.assertEqual((code, pre["ok"]), (200, True))
        for index, step in enumerate(STEPS, 1):
            body = self.payload(step_id=f"step-{index:03d}-{step['action']}",
                                action=step["action"], params=step["params"])
            code, result = self.post("/actions/execute", body)
            self.assertEqual((code, result["duplicate"]), (200, False))
            if index == 1:
                code, duplicate = self.post("/actions/execute", body)
                self.assertEqual((code, duplicate["duplicate"]), (200, True))
        self.assertEqual(len(server.brain.inbox.receipts), 3)
        code, verified = self.post("/actions/verify", self.payload())
        self.assertEqual((code, verified["ok"]), (200, True))
        self.assertEqual(len(verified["receipt_ids"]), 3)

    def test_unapproved_protocol_is_rejected(self):
        code, result = self.post("/actions/preconditions", self.payload())
        self.assertEqual(code, 409)
        self.assertFalse(result["checks"]["protocol_armed"])

    def test_wrong_trigger_is_rejected(self):
        server.brain.store.approve(self.pid, "owner")
        code, result = self.post("/actions/preconditions",
                                 self.payload(trigger_class="fyi_noise"))
        self.assertEqual(code, 409)
        self.assertFalse(result["checks"]["trigger_matches"])

    def test_non_allowlisted_action_is_rejected(self):
        server.brain.store.approve(self.pid, "owner")
        code, result = self.post("/actions/preconditions",
                                 self.payload(planned_actions=["delete_account"]))
        self.assertEqual(code, 409)
        self.assertFalse(result["checks"]["actions_allowlisted"])

    def test_unknown_event_is_rejected(self):
        server.brain.store.approve(self.pid, "owner")
        code, result = self.post("/actions/preconditions",
                                 self.payload(event_id="evt-missing"))
        self.assertEqual(code, 409)
        self.assertFalse(result["checks"]["event_exists"])

    def test_execute_requires_successful_precheck(self):
        server.brain.store.approve(self.pid, "owner")
        code, result = self.post("/actions/execute", self.payload(
            step_id="step-001-forward", action="forward", params=STEPS[0]["params"]))
        self.assertEqual(code, 400)
        self.assertIn("preconditions", result["error"])

    def test_step_order_and_params_are_enforced(self):
        server.brain.store.approve(self.pid, "owner")
        self.post("/actions/preconditions", self.payload())
        code, out_of_order = self.post("/actions/execute", self.payload(
            step_id="step-002-label", action="label", params=STEPS[1]["params"]))
        self.assertEqual(code, 400)
        self.assertIn("out of order", out_of_order["error"])
        code, wrong_params = self.post("/actions/execute", self.payload(
            step_id="step-001-forward", action="forward", params={"to": "attacker@example.com"}))
        self.assertEqual(code, 400)
        self.assertIn("params", wrong_params["error"])
        self.assertEqual(server.brain.inbox.receipts, [])


if __name__ == "__main__":
    unittest.main()
