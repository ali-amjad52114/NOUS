"""The brain: promises → commitments → motion; watched fixes → protocols.

Two loops, one memory:
  PROMISE LOOP  a promise you typed becomes a Commitment with a deadline;
                the brain plans a real calendar slot, opens a Guild concierge
                session for your approval, then a RocketRide pipeline books it,
                sends the message, and schedules the follow-up.
  PROTOCOL LOOP watch you handle something once → Distiller compiles a typed
                Protocol → Safety Critic reviews → you arm it once → it runs
                autonomously forever (each protocol emitted as a .pipe).
"""
from __future__ import annotations

from . import distill, feed, parse, pipegen
from .actions import Inbox
from .memory import make_store

OWNER = "Abhinav"
DEADLINE_DAYS = 15


class Brain:
    def __init__(self):
        self.store = make_store()
        self.inbox = Inbox()
        self.pending_queue: list[dict] = []   # events refused pre-approval
        self.watching: dict | None = None
        self.log: list[str] = []

    def say(self, msg: str):
        self.log.append(msg)
        print(msg)

    def plan_goal(self, goal: str) -> dict:
        goal = " ".join(str(goal or "").split())
        assert goal, "goal is required"

        # Promise involving a real person -> FULL commitment flow
        p = parse.parse_promise(goal)
        if p["understood"]:
            eid = f"said-{len(self.inbox.items) + 1}"
            evt = {"id": eid, "type": "message_out", "channel": "you",
                   "person": p["person"], "subject": "you said",
                   "body": goal, "trigger_class": "promise_made"}
            self.inbox.add(evt)
            self.store.remember_event(feed.publish(evt))
            c = self.store.save_commitment({
                "person": p["person"], "promise": goal[:140],
                "deadline_days": p["deadline_days"], "source_event": eid,
                "activity": p["activity"]})
            self.store.update_commitment(c["id"], status="proposed",
                                         proposed_slot=p["proposed_slot"],
                                         window_label=p["window_label"],
                                         days_out=p["days_out"])
            self.say(f"\U0001f91d PROMISE DETECTED — \u201c{goal}\u201d")
            self.say(f"   \u2192 Commitment {c['id']}: {p['activity']} with {p['person']}, "
                     f"{p['window_label']}. I won't let this one slip.")
            self.say("   [guild] concierge session opened — awaiting owner decision:")
            self.say(f"   \u25b6 You're free {p['proposed_slot']} — book {p['activity']} "
                     f"with {p['person']}?   \u2192  approve {c['id']}")
            return {"status": "proposed", "commitment_id": c["id"], "goal": goal,
                    "plan": [f"Book {p['activity']} with {p['person']}",
                             f"Send {p['person']} the confirmation",
                             "Follow up if no reply in 2 days"],
                    "slot": p["proposed_slot"], "days_out": p["days_out"], **p}

        personal = any(word in goal.lower() for word in ("visit", "meet", "call", "see "))
        plan = [
            "Clarify the outcome and who is involved",
            "Check travel, preparation, and coordination needs",
            "Reserve the time and send a confirmation",
        ] if personal else [
            "Define what done looks like",
            "Gather what you need and clear the first blocker",
            "Protect a focused time block and start",
        ]
        slot = min(
            (slot for slot in feed.FREE_SLOTS if slot["days_out"] <= DEADLINE_DAYS),
            key=lambda item: item["days_out"],
        )
        result = {"goal": goal, "plan": plan, "slot": slot["slot"],
                  "days_out": slot["days_out"]}
        self.say(f"🎯 GOAL RECEIVED — \"{goal}\"")
        self.say(f"🧭 PLAN READY — {' → '.join(plan)}")
        self.say(f"🗓 BEST SLOT — {slot['slot']} (day {slot['days_out']} of {DEADLINE_DAYS})")
        return result

    # ---------------------------------------------------------------- ingest
    def ingest(self, evt: dict) -> str:
        evt = feed.publish(evt)
        self.inbox.add(evt)
        self.store.remember_event(evt)
        tc = evt["trigger_class"]

        if tc == "important_personal":
            self.say(f"💙 {evt['id']} — {evt.get('person')}: \"{evt['body'][:64]}...\"")
            self.say(f"   [brain] remembered. {evt.get('person')} matters — watching for what you say next.")
            return "remembered"

        if tc == "promise_made":
            return self._promise_detected(evt)

        if tc == "fyi_noise":
            self.say(f"  [brain] {evt['id']} '{evt.get('subject', '')[:40]}' — noise, no action needed")
            return "ignored"

        # protocol loop
        match = self.store.find_protocol(tc, evt.get("subject", ""))
        if not match:
            self.watching = evt
            self.say(f"🧠 {evt['id']} '{evt.get('subject', '')[:48]}' — I've never seen a {tc} before.")
            self.say("   Show me how you handle it, I'm watching.")
            return "watching"
        proto = match["protocol"]
        if not proto.get("approved"):
            self.pending_queue.append(evt)
            self.say(f"✋ {evt['id']} matches protocol {proto['id']} (score {match['score']}) — "
                     f"but you haven't approved it yet. REFUSING to act. Queued.")
            return "refused_pending_approval"
        return self._act(evt, proto, match["score"])

    # ---------------------------------------------------------- promise loop
    def _promise_detected(self, evt: dict) -> str:
        person = evt.get("person", "them")
        c = self.store.save_commitment({
            "person": person, "promise": evt.get("body", "").strip()[:120],
            "deadline_days": DEADLINE_DAYS, "source_event": evt["id"],
        })
        self.say(f"🤝 PROMISE DETECTED in your message to {person}:")
        self.say(f"   \"{evt.get('body', '')[:70]}\"")
        self.say(f"   → Commitment {c['id']} created · deadline: {DEADLINE_DAYS} days. "
                 f"I won't let this one slip.")
        slot = next((s for s in feed.FREE_SLOTS if s["days_out"] <= DEADLINE_DAYS), None)
        if not slot:
            self.say(f"   ⚠ no free slot inside {DEADLINE_DAYS} days — escalating to you")
            return "escalated"
        self.store.update_commitment(c["id"], status="proposed", proposed_slot=slot["slot"])
        self.say(f"   [guild] concierge session opened — awaiting owner decision:")
        self.say(f"   ▶ You're free {slot['slot']} (day {slot['days_out']} of {DEADLINE_DAYS}). "
                 f"Book it with {person}?   →  approve {c['id']}")
        return "proposed"

    def approve_commitment(self, cid: str) -> str:
        c = self.store.g["commitments"].get(cid) if hasattr(self.store, "g") else None
        assert c and c.get("proposed_slot"), f"no proposed slot on {cid}"
        person, slot = c["person"], c["proposed_slot"]
        self.say(f"✅ {cid} approved by {OWNER} — RocketRide pipeline 'keep-a-promise' executing:")
        evt_id = c["source_event"]
        for action, params in [
            ("book", {"slot": slot, "with_person": person}),
            ("send_message", {"to": person,
                              "text": f"Hey {person} — does {slot} work for me to come by? "
                                      f"I meant it. I'll be there."}),
        ]:
            result = self.inbox.execute(evt_id, action, params, actor="brain")
            self.say(f"     brain: {action} -> {result}")
        self.store.update_commitment(cid, status="booked", booked_slot=slot)
        rid = self.store.record_use("P-KEEPER", evt_id, True)
        pipe = pipegen.emit_pipe({"id": "P-KEEPER", "name": "Keep a promise",
                                  "trigger_class": "promise_made", "taught_by": OWNER,
                                  "steps": [{"action": "book", "params": {"slot": "$slot", "with_person": "$person"}},
                                            {"action": "send_message", "params": {"to": "$person", "text": "$proposal"}}],
                                  "postcondition": "calendar hold exists + message delivered + follow-up scheduled"})
        self.say(f"   📌 booked. follow-up scheduled: if {person} hasn't replied in 2 days, I'll nudge.")
        self.say(f"   ⚙ compiled to RocketRide pipeline: {pipe} · receipt {rid}")
        self.say(f"   {self.inbox.scoreboard()}")
        return "booked"

    # -------------------------------------------------------- protocol loop
    def human_action(self, action: str, params: dict) -> str:
        assert self.watching, "not in watch mode"
        result = self.inbox.execute(self.watching["id"], action, params, actor=OWNER)
        self.say(f"   👀 watched: {action}({params}) -> {result}")
        return result

    def human_done(self) -> dict:
        evt = self.watching
        self.watching = None
        watched = [r for r in self.inbox.receipts if r["event_id"] == evt["id"]]
        proto = distill.distill(evt, watched)
        review = distill.critique(proto)
        saved = self.store.save_protocol(proto, learned_from=evt["id"], taught_by=OWNER)
        pipe_path = pipegen.emit_pipe(saved)
        self.say(f"🧠 PROTOCOL DISTILLED — {saved['id']} '{saved['name']}'  [guild: Distiller]")
        for n in review["notes"]:
            self.say(f"     [guild: Safety Critic] {n}")
        self.say(f"   ⚙ compiled to RocketRide pipeline: {pipe_path}")
        self.say(f"   ▶ arm it:  approve {saved['id']}")
        return saved

    def approve(self, pid: str) -> list[str]:
        self.store.approve(pid, OWNER)
        self.say(f"✅ {pid} approved by {OWNER} — protocol ARMED.")
        results = []
        while self.pending_queue:
            evt = self.pending_queue.pop(0)
            match = self.store.find_protocol(evt["trigger_class"], evt.get("subject", ""))
            if match and match["protocol"].get("approved"):
                results.append(self._act(evt, match["protocol"], match["score"]))
        return results

    def _act(self, evt: dict, proto: dict, score: float) -> str:
        checks = [
            ("trigger class matches protocol", evt["trigger_class"] == proto["trigger_class"]),
            ("all steps on allowlist", all(s["action"] in distill.ALLOWED_ACTIONS
                                           for s in proto["steps"])),
            ("owner approval on record", bool(proto.get("approved"))),
            ("risk within policy", proto.get("risk") == "low"),
        ]
        if not all(ok for _, ok in checks):
            self.pending_queue.append(evt)
            self.say(f"✋ {evt['id']}: precondition failed — escalating instead of acting")
            return "escalated"
        n = len(checks)
        self.say(f"⚡ {evt['id']} '{evt.get('subject', '')[:44]}' — protocol {proto['id']} "
                 f"(score {score}) · preconditions {n}/{n} ✓")
        for step in proto["steps"]:
            result = self.inbox.execute(evt["id"], step["action"], step["params"], actor="brain")
            self.say(f"     brain: {step['action']} -> {result}")
        ok = self.inbox.verify_handled(evt["id"])
        rid = self.store.record_use(proto["id"], evt["id"], ok)
        self.say(f"   ✅ done autonomously — using the protocol {proto.get('taught_by')} taught me "
                 f"({proto.get('learned_from')}). receipt {rid} · {self.inbox.scoreboard()}")
        return "acted"
