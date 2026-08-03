import json
import re
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer

import server
from kit.brain import Brain
from kit.feed import FREE_SLOTS, STORY


class DashboardHandlerTest(unittest.TestCase):
    dashboard_path = server.ROOT / "frontend" / "index.html"

    def test_dashboard_is_served_from_root(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        try:
            with urlopen(f"http://127.0.0.1:{httpd.server_port}/") as response:
                body = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), "text/html")
                self.assertIn("<title>Nous — Personal brain</title>", body)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join()

    def test_dashboard_embeds_the_story_in_feed_order(self):
        body = self.dashboard_path.read_text()
        match = re.search(
            r'<script id="story-data" type="application/json">(.*?)</script>',
            body,
            re.DOTALL,
        )

        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1)), STORY)

    def test_dashboard_exposes_the_goal_planning_composer(self):
        body = self.dashboard_path.read_text()

        self.assertIn('<form class="goal-composer" id="goal-form">', body)
        self.assertIn('name="goal"', body)
        self.assertIn('type="submit">Find the best time</button>', body)

    def test_dashboard_declares_the_required_action_contracts(self):
        body = self.dashboard_path.read_text()
        match = re.search(
            r'<script id="action-contracts" type="application/json">(.*?)</script>',
            body,
            re.DOTALL,
        )

        self.assertIsNotNone(match)
        self.assertEqual(
            json.loads(match.group(1)),
            {
                "watchActions": [
                    {"label": "Forward", "body": {"action": "forward", "params": {"to": "accounting@myfirm.com"}}},
                    {"label": "Label invoices", "body": {"action": "label", "params": {"name": "invoices"}}},
                    {"label": "Archive", "body": {"action": "archive", "params": {}}},
                ],
                "watchDone": {},
                "approveProtocol": {"protocol_id": "P-001"},
                "approveCommitment": {"commitment_id": "C-001"},
            },
        )

    def test_goal_endpoint_returns_a_plan_and_the_best_free_slot(self):
        original_brain = server.brain
        server.brain = Brain()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        try:
            request = Request(
                f"http://127.0.0.1:{httpd.server_port}/goals",
                data=json.dumps({"goal": "Visit Sam before chemo starts"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request) as response:
                payload = json.loads(response.read())

            self.assertEqual(payload["goal"], "Visit Sam before chemo starts")
            self.assertEqual(payload["slot"], FREE_SLOTS[0]["slot"])
            self.assertEqual(len(payload["plan"]), 3)
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join()
            server.brain = original_brain

    def test_goal_endpoint_rejects_an_empty_goal(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        try:
            request = Request(
                f"http://127.0.0.1:{httpd.server_port}/goals",
                data=json.dumps({"goal": "   "}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as raised:
                urlopen(request)

            self.assertEqual(raised.exception.code, 400)
            self.assertEqual(json.loads(raised.exception.read()), {"error": "goal is required"})
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
