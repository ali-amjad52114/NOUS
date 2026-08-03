import json
import re
import threading
import unittest
from urllib.request import urlopen

from http.server import ThreadingHTTPServer

import server
from kit.feed import STORY


class DashboardHandlerTest(unittest.TestCase):
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
        body = (server.ROOT / "index.html").read_text()
        match = re.search(
            r'<script id="story-data" type="application/json">(.*?)</script>',
            body,
            re.DOTALL,
        )

        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1)), STORY)

    def test_dashboard_declares_the_required_action_contracts(self):
        body = (server.ROOT / "index.html").read_text()
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


if __name__ == "__main__":
    unittest.main()
