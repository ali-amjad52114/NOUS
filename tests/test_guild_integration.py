import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integrations.guild import GuildIntegrationError, review_protocol
from integrations.guild import guild_runner
from integrations.guild.schemas import SchemaError, validate_critic_output, validate_protocol
from kit import distill
from kit.brain import Brain
from kit.memory import LocalStore

FIXTURES = Path(__file__).resolve().parents[1] / "integrations" / "guild" / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


class GuildContractTests(unittest.TestCase):
    def test_valid_invoice_is_eligible_with_provenance(self):
        data = fixture("valid_invoice.json")
        with patch.dict(os.environ, {"GUILD_MODE": "fallback"}, clear=False):
            result = review_protocol(data["event"], data["receipts"], "owner-1")
        self.assertEqual(result["review"]["verdict"], "APPROVE_ELIGIBLE")
        self.assertTrue(result["provenance"]["guild_schema_validated"])
        self.assertTrue(result["provenance"]["guild_distiller_session"].startswith("fallback-"))
        self.assertIn("distiller", result["provenance"]["guild_agent_ids"])
        self.assertIn("critic", result["provenance"]["guild_agent_versions"])

    def test_live_distiller_output_is_the_exact_critic_input(self):
        data = fixture("valid_invoice.json")
        protocol = distill.distill(data["event"], data["receipts"])
        review = distill.critique(protocol)
        calls = [
            (protocol, {"session": "s-distill", "version": "v-distill", "agent": "a-distill"}),
            (review, {"session": "s-critic", "version": "v-critic", "agent": "a-critic"}),
        ]
        with patch.dict(os.environ, {"GUILD_MODE": "live"}, clear=False), \
                patch.object(guild_runner, "_live_agent", side_effect=calls) as live:
            result = guild_runner.review_protocol(data["event"], data["receipts"], "owner-1")
        self.assertEqual(live.call_args_list[1].args[1]["protocol"], protocol)
        self.assertEqual(result["provenance"]["guild_distiller_session"], "s-distill")
        self.assertEqual(result["provenance"]["guild_critic_session"], "s-critic")
        self.assertEqual(result["provenance"]["critic_verdict"], "APPROVE_ELIGIBLE")

    def test_reject_is_persisted_but_cannot_be_armed(self):
        data = fixture("valid_invoice.json")
        protocol = distill.distill(data["event"], data["receipts"])
        review = {"verdict": "REJECT", "findings": [{"number": 1, "code": "TEST_REJECT",
                  "message": "adversarial rejection", "severity": "critical"}],
                  "residual_risk": "Unsafe until corrected.",
                  "checks": {"allowlisted_actions": True, "parameterized_inputs": False,
                             "approval_precondition": True, "verifiable_postcondition": True}}
        provenance = {"guild_mode": "live", "guild_schema_validated": True,
                      "guild_distiller_session": "s-distill", "guild_critic_session": "s-critic",
                      "guild_agent_ids": {"distiller": "a-distill", "critic": "a-critic"},
                      "guild_agent_versions": {"distiller": "v-distill", "critic": "v-critic"},
                      "critic_verdict": "REJECT", "critic_findings": review["findings"],
                      "critic_residual_risk": review["residual_risk"], "critic_checks": review["checks"]}
        with tempfile.TemporaryDirectory() as tmp:
            brain = Brain()
            brain.store = LocalStore(Path(tmp) / "memory.json")
            event = {**data["event"], "from": "vendor@example.com"}
            brain.watching = event
            brain.inbox.add(event)
            for receipt in data["receipts"]:
                brain.human_action(receipt["action"], receipt["params"])
            with patch("kit.brain.review_protocol", return_value={"protocol": protocol,
                       "review": review, "provenance": provenance}), \
                    patch("kit.brain.pipegen.emit_pipe", return_value="mock.pipe"):
                saved = brain.human_done()
            self.assertEqual(saved["critic_verdict"], "REJECT")
            self.assertFalse(saved["approved"])
            with self.assertRaises(ValueError):
                brain.approve(saved["id"])

    def test_forbidden_action_fails_closed(self):
        data = fixture("forbidden_action.json")
        self.assertEqual(distill.critique(data["protocol"])["verdict"], "REJECT")
        with self.assertRaises(SchemaError):
            validate_protocol(data["protocol"])

    def test_hardcoded_vendor_is_rejected(self):
        data = fixture("hardcoded_vendor.json")
        self.assertEqual(distill.critique(data["protocol"])["verdict"], "REJECT")

    def test_missing_approval_is_rejected(self):
        data = fixture("missing_approval.json")
        self.assertEqual(distill.critique(data["protocol"])["verdict"], "REJECT")

    def test_unverifiable_postcondition_fails_closed(self):
        data = fixture("unverifiable_postcondition.json")
        self.assertEqual(distill.critique(data["protocol"])["verdict"], "REJECT")
        with self.assertRaises(SchemaError):
            validate_protocol(data["protocol"])

    def test_malformed_critic_output_fails_closed(self):
        data = fixture("malformed_output.json")
        with self.assertRaises(SchemaError):
            validate_critic_output(data["raw_output"])

    def test_schema_failure_is_normalized_for_product_layer(self):
        data = fixture("valid_invoice.json")
        with patch.dict(os.environ, {"GUILD_MODE": "fallback"}, clear=False), \
                patch.object(guild_runner.local, "distill", return_value={}):
            with self.assertRaisesRegex(GuildIntegrationError, "schema validation"):
                guild_runner.review_protocol(data["event"], data["receipts"], "owner-1")

    def test_brain_approval_cannot_bypass_guild_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Brain()
            brain.store = LocalStore(Path(tmp) / "memory.json")
            saved = brain.store.save_protocol({"name": "unsafe", "trigger_class": "x"}, "evt", "owner")
            with self.assertRaises(ValueError):
                brain.approve(saved["id"])

    def test_live_configuration_failure_leaves_watching_and_persists_nothing(self):
        brain = Brain()
        brain.store.reset()
        event = {"id": "evt-live-fail", "type": "message_in", "channel": "gmail",
                 "subject": "Invoice needs review", "body": "Amount due", "attachment": "invoice.pdf",
                 "from": "vendor@example.com", "ts": 1}
        with patch.dict(os.environ, {"GUILD_MODE": "live", "GUILD_WORKSPACE_OWNER": "",
                                    "GUILD_WORKSPACE_NAME": "", "GUILD_DISTILLER_CREDENTIALS": "",
                                    "GUILD_CRITIC_CREDENTIALS": ""}, clear=False):
            self.assertEqual(brain.ingest(event), "watching")
            brain.human_action("archive", {})
            with self.assertRaises(GuildIntegrationError):
                brain.human_done()
        self.assertEqual(brain.watching["id"], event["id"])
        self.assertFalse(brain.store.g["protocols"])
        self.assertIsNotNone(brain.guild_error)


if __name__ == "__main__":
    unittest.main()
