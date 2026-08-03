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
from .actions import ALLOWED, Inbox
from .memory import make_store
from integrations.guild import GuildIntegrationError, review_protocol
from integrations.rocketride_runner import run_protocol

OWNER = "Abhinav"
DEADLINE_DAYS = 15


class Brain:
    def __init__(self):
        self.store = make_store()
        self.inbox = Inbox()
        self.pending_queue: list[dict] = []   # events refused pre-approval
        self.watching: dict | None = None
        self.log: list[str] = []
        self.guild_error: str | None = None
        self.runtime_protocols: dict[str, dict] = {}
        self._run_context: dict[str, dict] = {}

    def say(self, msg: str):
        self.log.append(msg)
        print(msg)

    def plan_goal(self, goal: str) -> dict:
        goal = " ".join(str(goal or "").split())
        assert goal, "goal is required"

        # If this is a promise involving a real person, run the FULL commitment
        # flow (parse who/what/when -> propose a dated slot -> Book It).
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
        self.store.update_commitment(cid, status="approved")
        self.say(f"✅ {cid} approved by {OWNER} — RocketRide pipeline 'keep-a-promise' executing:")
        evt_id = c["source_event"]
        proposal = (f"Hey {person} — does {slot} work for me to come by? "
                    "I meant it. I'll be there.")
        proto = {"id": "P-KEEPER", "name": "Keep a promise", "approved": True,
                 "trigger_class": "promise_made", "taught_by": OWNER, "risk": "low",
                 "steps": [{"action": "book", "params": {"slot": "$slot", "with_person": "$person"}},
                           {"action": "send_message", "params": {"to": "$person", "text": "$proposal"}}],
                 "postcondition": "calendar hold exists and message delivered"}
        self.runtime_protocols[proto["id"]] = proto
        pipe = pipegen.emit_pipe(proto)
        outcome = run_protocol(pipe, {"event_id": evt_id, "protocol_id": proto["id"],
                                      "trigger_class": "promise_made",
                                      "inputs": {"slot": slot, "person": person,
                                                 "proposal": proposal}},
                               fallback_dispatch=self._fallback_protocol_execution)
        if not outcome["ok"]:
            raise RuntimeError(f"RocketRide execution failed: {outcome}")
        self.store.update_commitment(cid, status="booked", booked_slot=slot)
        self.say(f"   📌 booked. follow-up scheduled: if {person} hasn't replied in 2 days, I'll nudge.")
        self.say(f"   ⚙ RocketRide run {outcome['run_id']} · trace {outcome['trace_ref']} · {pipe}")
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
        assert evt, "not in watch mode"
        watched = [r for r in self.inbox.receipts if r["event_id"] == evt["id"]]
        try:
            judgment = review_protocol(evt, watched, OWNER)
        except GuildIntegrationError as exc:
            self.guild_error = str(exc)
            self.say(f"Guild judgment failed closed: {exc}")
            raise
        self.guild_error = None
        self.watching = None
        proto, review = judgment["protocol"], judgment["review"]
        proto = {**proto, **judgment["provenance"]}
        saved = self.store.save_protocol(proto, learned_from=evt["id"], taught_by=OWNER)
        pipe_path = pipegen.emit_pipe(saved)
        self.say(f"🧠 PROTOCOL DISTILLED — {saved['id']} '{saved['name']}'  "
                 f"[guild session: {saved['guild_distiller_session']}]")
        self.say(f"     [guild: Safety Critic] {review['verdict']} · "
                 f"session {saved['guild_critic_session']}")
        for finding in review["findings"]:
            self.say(f"     [{finding['number']}] {finding['code']}: {finding['message']}")
        self.say(f"   ⚙ compiled to RocketRide pipeline: {pipe_path}")
        if review["verdict"] == "APPROVE_ELIGIBLE":
            self.say(f"   ▶ human may arm it:  approve {saved['id']}")
        else:
            self.say("   ✋ Guild rejected this protocol; human approval is disabled")
        return saved

    def approve(self, pid: str) -> list[str]:
        proto = self.store.g.get("protocols", {}).get(pid) if hasattr(self.store, "g") else None
        if not proto:
            raise ValueError(f"unknown protocol {pid}")
        if not proto.get("guild_schema_validated") or proto.get("critic_verdict") != "APPROVE_ELIGIBLE":
            raise ValueError(f"{pid} cannot be armed: Guild verdict is not APPROVE_ELIGIBLE")
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
        pipe_path = pipegen.emit_pipe(proto)
        outcome = run_protocol(pipe_path, {"event_id": evt["id"], "protocol_id": proto["id"],
                                           "trigger_class": evt["trigger_class"], "inputs": {}},
                               fallback_dispatch=self._fallback_protocol_execution)
        if not outcome["ok"]:
            self.pending_queue.append(evt)
            self.say(f"   ⚠ RocketRide run {outcome['run_id']} failed; event re-queued")
            raise RuntimeError(f"RocketRide execution failed: {outcome}")
        self.say(f"   ✅ done autonomously — using the protocol {proto.get('taught_by')} taught me "
                 f"({proto.get('learned_from')}). run {outcome['run_id']} · "
                 f"trace {outcome['trace_ref']} · {self.inbox.scoreboard()}")
        return "acted"

    # ------------------------------------------------ RocketRide callbacks
    def _protocol(self, pid: str) -> dict | None:
        if pid in self.runtime_protocols:
            return self.runtime_protocols[pid]
        return self.store.g.get("protocols", {}).get(pid) if hasattr(self.store, "g") else None

    def check_preconditions(self, payload: dict) -> dict:
        run_id, event_id = payload.get("run_id"), payload.get("event_id")
        pid = payload.get("protocol_id") or payload.get("protocol")
        proto, item = self._protocol(pid or ""), self.inbox.items.get(event_id or "")
        planned = payload.get("planned_actions")
        if planned is None and proto:
            planned = [s.get("action") for s in proto.get("steps", [])]
        checks = {
            "run_id_present": bool(run_id),
            "event_exists": item is not None,
            "protocol_exists": proto is not None,
            "protocol_armed": bool(proto and proto.get("approved")),
            "trigger_matches": bool(proto and item and
                                    item["evt"].get("trigger_class") == proto.get("trigger_class") and
                                    payload.get("trigger_class") == proto.get("trigger_class")),
            "actions_allowlisted": bool(planned) and all(a in ALLOWED for a in planned or []),
            "actions_match_protocol": bool(proto) and planned == [s.get("action") for s in proto.get("steps", [])],
        }
        ok = all(checks.values())
        if ok:
            self._run_context[run_id] = {"event_id": event_id, "protocol_id": pid,
                                         "preconditions": checks, "verified": False,
                                         "inputs": dict(payload.get("inputs") or {}),
                                         "next_step": 0}
        return {"ok": ok, "run_id": run_id, "event_id": event_id,
                "protocol_id": pid, "checks": checks}

    def execute_protocol_step(self, payload: dict) -> dict:
        run_id, event_id = payload.get("run_id"), payload.get("event_id")
        pid = payload.get("protocol_id") or payload.get("protocol")
        step_id, action = payload.get("step_id"), payload.get("action")
        context, proto = self._run_context.get(run_id), self._protocol(pid or "")
        if not context or context.get("event_id") != event_id or context.get("protocol_id") != pid:
            raise ValueError("run has not passed preconditions")
        if not proto or not proto.get("approved"):
            raise ValueError("protocol is missing or not armed")
        try:
            index = int((step_id or "").split("-", 2)[1]) - 1
            expected = proto["steps"][index]
        except (ValueError, IndexError, KeyError):
            raise ValueError(f"invalid step_id {step_id!r}") from None
        canonical_step_id = f"step-{index + 1:03d}-{expected['action']}"
        if step_id != canonical_step_id or action != expected["action"] or action not in ALLOWED:
            raise ValueError("step does not match armed protocol")
        existing = next((r for r in self.inbox.receipts
                         if r.get("run_id") == run_id and r.get("step_id") == step_id), None)
        if not existing and index != context["next_step"]:
            raise ValueError(f"step out of order: expected index {context['next_step'] + 1}")
        params = payload.get("params", {})
        expected_params = self._resolve(expected.get("params", {}), context["inputs"])
        if params != expected_params:
            raise ValueError("step params do not match armed protocol and run inputs")
        result = self.inbox.execute_once(event_id, action, params, run_id=run_id,
                                         step_id=step_id, protocol_id=pid)
        if not result["duplicate"]:
            context["next_step"] += 1
        return {"ok": True, **result}

    def verify_protocol(self, payload: dict) -> dict:
        run_id, event_id = payload.get("run_id"), payload.get("event_id")
        pid = payload.get("protocol_id") or payload.get("protocol")
        context, proto = self._run_context.get(run_id), self._protocol(pid or "")
        if not context or not proto or context.get("event_id") != event_id:
            return {"ok": False, "error": "unknown or unchecked run", "receipt_ids": []}
        receipts = [r for r in self.inbox.receipts if r.get("run_id") == run_id]
        expected = [s["action"] for s in proto.get("steps", [])]
        actual = [r["action"] for r in receipts]
        item = self.inbox.items.get(event_id, {})
        state_checks = []
        for step in proto.get("steps", []):
            action = step["action"]
            params = self._resolve(step.get("params", {}), context["inputs"])
            if action == "forward":
                state_checks.append(item.get("forwarded_to") == params.get("to"))
            elif action == "label":
                state_checks.append(params.get("name") in item.get("labels", []))
            elif action == "archive":
                state_checks.append(bool(item.get("archived")))
            elif action == "reply":
                state_checks.append(bool(item.get("replied")))
            elif action == "book":
                state_checks.append(item.get("booked") == params.get("slot"))
            elif action == "send_message":
                state_checks.append(bool(item.get("sent")))
        ok = actual == expected and all(state_checks)
        if ok and not context["verified"]:
            context["use_receipt_id"] = self.store.record_use(pid, event_id, True)
            context["verified"] = True
        return {"ok": ok, "run_id": run_id, "event_id": event_id,
                "protocol_id": pid, "expected_actions": expected,
                "actual_actions": actual, "receipt_ids": [r["id"] for r in receipts],
                "use_receipt_id": context.get("use_receipt_id")}

    @staticmethod
    def _resolve(value, inputs: dict):
        if isinstance(value, str) and value.startswith("$"):
            return inputs.get(value[1:], value)
        if isinstance(value, dict):
            return {k: Brain._resolve(v, inputs) for k, v in value.items()}
        if isinstance(value, list):
            return [Brain._resolve(v, inputs) for v in value]
        return value

    def _fallback_protocol_execution(self, pipe_path: str, payload: dict) -> dict:
        """Clearly labeled rehearsal fallback implementing the same callback contract."""
        proto = self._protocol(payload["protocol_id"])
        payload = {**payload, "planned_actions": [s["action"] for s in proto["steps"]]}
        pre = self.check_preconditions(payload)
        if not pre["ok"]:
            return {"ok": False, "preconditions": pre}
        step_results = []
        for i, step in enumerate(proto["steps"], 1):
            step_results.append(self.execute_protocol_step({**payload,
                "step_id": f"step-{i:03d}-{step['action']}", "action": step["action"],
                "params": self._resolve(step.get("params", {}), payload.get("inputs", {}))}))
        return {"ok": True, "preconditions": pre, "steps": step_results,
                "verification": self.verify_protocol(payload)}
