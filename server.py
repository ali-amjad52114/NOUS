#!/usr/bin/env python3
"""The team contract as a running server — same three endpoints you agreed on,
plus approve/state. Person 1's UI drives this; Person 3's RocketRide pipes
call back into /actions/execute so the ENGINE is the execution path.

    python3 server.py          # -> http://127.0.0.1:7200

  POST /events            {event json}           -> brain ingests (watch/refuse/act)
  GET  /memory/similar    ?trigger_class=&q=     -> best matching protocol
  POST /actions/execute   {event_id, action, params, protocol?} -> allowlisted execution
  POST /actions/preconditions | /actions/verify  -> pipeline check hooks
  POST /watch/action      {action, params}       -> human handles item (brain watching)
  POST /watch/done        {}                     -> distill + critic + compile .pipe
  POST /approve           {protocol_id}          -> arm + drain refused queue
  GET  /state                                    -> inbox, protocols, scoreboard, log
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kit.brain import Brain  # noqa: E402

brain = Brain()
PORT = 7200


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        if self.path.startswith("/memory/similar"):
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            m = brain.store.find_protocol(qs.get("trigger_class", [""])[0], qs.get("q", [""])[0])
            self._send(200, m or {"match": None})
        elif self.path == "/state":
            self._send(200, {"scoreboard": brain.inbox.scoreboard(),
                             "graph": brain.store.describe(),
                             "pending_queue": [e["id"] for e in brain.pending_queue],
                             "watching": (brain.watching or {}).get("id"),
                             "log": brain.log[-30:]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        b = self._body()
        try:
            if self.path == "/events":
                self._send(200, {"status": brain.ingest(b)})
            elif self.path == "/actions/execute":
                actor = "brain" if b.get("protocol") else "human"
                r = brain.inbox.execute(b["event_id"], b["action"], b.get("params", {}), actor)
                self._send(200, {"ok": True, "result": r})
            elif self.path == "/actions/preconditions":
                self._send(200, {"ok": True})   # pipeline precondition hook
            elif self.path == "/actions/verify":
                self._send(200, {"ok": brain.inbox.verify_handled(b.get("event_id", ""))})
            elif self.path == "/watch/action":
                self._send(200, {"result": brain.human_action(b["action"], b.get("params", {}))})
            elif self.path == "/watch/done":
                self._send(200, {"protocol": brain.human_done()})
            elif self.path == "/approve":
                self._send(200, {"acted_on": brain.approve(b["protocol_id"])})
            elif self.path == "/approve-commitment":
                self._send(200, {"status": brain.approve_commitment(b["commitment_id"])})
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(400, {"error": str(e)})


if __name__ == "__main__":
    print(f"personal brain online :{PORT} — POST /events to feed it")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
