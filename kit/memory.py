"""Protocol memory — the FalkorDB layer.

Graph: (:Event)-[:OF_CLASS]->(:TriggerClass)
       (:Protocol)-[:HANDLES]->(:TriggerClass)
       (:Protocol)-[:LEARNED_FROM]->(:Event)
       (:Protocol)-[:TAUGHT_BY]->(:Person)  (:Protocol)-[:APPROVED_BY]->(:Person)
       (:Receipt)-[:RAN]->(:Protocol)       (:Receipt)-[:ON]->(:Event)
       (:Contact)  — people/vendors the brain has met (memory compounds)

LocalStore (zero-dep, JSON-persisted) and FalkorStore share one interface —
flip with MEMORY_BACKEND=falkor once docker + `pip install falkordb` are up.
Judge query for the FalkorDB browser (:3000):
    MATCH (p:Protocol)-[r]->(x) RETURN p, r, x
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state"


def _tokens(t: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", (t or "").lower()) if len(w) > 1}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


class LocalStore:
    def __init__(self, path: Path | None = None):
        self.path = path or (STATE / "brain_memory.json")
        self.g = {"protocols": {}, "events": {}, "contacts": {}, "receipts": {},
                  "commitments": {}}
        if self.path.exists():
            try:
                self.g.update(json.loads(self.path.read_text()))
            except Exception:
                pass
        self.g.setdefault("commitments", {})

    def _save(self):
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(self.g, indent=2))

    def remember_event(self, evt: dict):
        self.g["events"][evt["id"]] = {k: evt.get(k) for k in
                                       ("id", "from", "subject", "trigger_class", "ts")}
        sender = evt.get("from", "")
        if sender:
            c = self.g["contacts"].setdefault(sender, {"name": sender, "seen": 0})
            c["seen"] += 1
        self._save()

    def save_protocol(self, proto: dict, learned_from: str, taught_by: str) -> dict:
        pid = f"P-{len(self.g['protocols']) + 1:03d}"
        proto = {**proto, "id": pid, "learned_from": learned_from, "taught_by": taught_by,
                 "approved": False, "created_ts": time.time(), "uses": 0}
        self.g["protocols"][pid] = proto
        self._save()
        return proto

    def find_protocol(self, trigger_class: str, signature: str):
        best, score = None, 0.0
        for p in self.g["protocols"].values():
            s = (0.7 if p.get("trigger_class") == trigger_class else 0.0) + \
                0.3 * similarity(signature, p.get("signature_example", ""))
            if s > score:
                best, score = p, s
        return {"protocol": dict(best), "score": round(score, 2)} if best and score >= 0.5 else None

    def approve(self, pid: str, approver: str):
        p = self.g["protocols"].get(pid)
        if p:
            p.update({"approved": True, "approved_by": approver, "approved_ts": time.time()})
            self._save()
        return p

    def save_commitment(self, c: dict) -> dict:
        cid = f"C-{len(self.g['commitments']) + 1:03d}"
        c = {**c, "id": cid, "status": "open", "created_ts": time.time()}
        self.g["commitments"][cid] = c
        self._save()
        return c

    def update_commitment(self, cid: str, **fields):
        c = self.g["commitments"].get(cid)
        if c:
            c.update(fields)
            self._save()
        return c

    def open_commitments(self) -> list[dict]:
        return [dict(c) for c in self.g["commitments"].values() if c["status"] != "kept"]

    def record_use(self, pid: str, event_id: str, ok: bool):
        rid = f"R-{len(self.g['receipts']) + 1:03d}"
        self.g["receipts"][rid] = {"id": rid, "protocol": pid, "event": event_id,
                                   "ok": ok, "ts": time.time()}
        if ok and pid in self.g["protocols"]:
            self.g["protocols"][pid]["uses"] += 1
        self._save()
        return rid

    def describe(self) -> str:
        out = [f"BRAIN GRAPH  protocols={len(self.g['protocols'])} events={len(self.g['events'])} "
               f"contacts={len(self.g['contacts'])} commitments={len(self.g['commitments'])} "
               f"receipts={len(self.g['receipts'])}"]
        for c in self.g["commitments"].values():
            out.append(f"  (:Commitment {c['id']}) to={c.get('person')} \"{c.get('promise', '')[:46]}\" "
                       f"deadline={c.get('deadline_days')}d [{c['status'].upper()}]"
                       + (f" → {c.get('booked_slot')}" if c.get('booked_slot') else ""))
        for p in self.g["protocols"].values():
            state = "ARMED" if p.get("approved") else "PENDING APPROVAL"
            out.append(f"  (:Protocol {p['id']}) '{p.get('name')}' class={p.get('trigger_class')} "
                       f"taught_by={p.get('taught_by')} uses={p.get('uses', 0)} [{state}]")
        for c in self.g["contacts"].values():
            out.append(f"  (:Contact '{c['name']}') seen={c['seen']}")
        return "\n".join(out)

    def reset(self):
        self.g = {"protocols": {}, "events": {}, "contacts": {}, "receipts": {},
                  "commitments": {}}
        self._save()


class FalkorStore(LocalStore):
    """Same interface, real graph. VENUE: docker run -p 6379:6379 -p 3000:3000
    falkordb/falkordb + pip install falkordb. Mirrors every write to Cypher so
    the browser shows the brain growing; reads still come from the local dict
    (fast + unkillable on stage)."""

    def __init__(self):
        super().__init__()
        from falkordb import FalkorDB  # guarded: only imported when selected
        self.graph = FalkorDB(host=os.environ.get("FALKOR_HOST", "localhost"),
                              port=int(os.environ.get("FALKOR_PORT", "6379"))
                              ).select_graph("personal_brain")

    @staticmethod
    def _q(s):  # escape for single-quoted Cypher strings
        return str(s).replace("\\", "\\\\").replace("'", "\\'")

    def remember_event(self, evt: dict):
        super().remember_event(evt)
        q, e = self._q, evt
        self.graph.query(f"MERGE (ev:Event {{id:'{q(e['id'])}'}}) "
                         f"SET ev.subject='{q(e.get('subject', ''))}', ev.sender='{q(e.get('from', ''))}'")
        self.graph.query(f"MERGE (t:TriggerClass {{name:'{q(e.get('trigger_class'))}'}})")
        self.graph.query(f"MATCH (ev:Event {{id:'{q(e['id'])}'}}), (t:TriggerClass {{name:'{q(e.get('trigger_class'))}'}}) "
                         f"MERGE (ev)-[:OF_CLASS]->(t)")
        if e.get("from"):
            self.graph.query(f"MERGE (c:Contact {{name:'{q(e['from'])}'}})")

    def save_protocol(self, proto, learned_from, taught_by):
        p = super().save_protocol(proto, learned_from, taught_by)
        q = self._q
        self.graph.query(
            f"MERGE (pr:Protocol {{id:'{q(p['id'])}'}}) SET pr.name='{q(p.get('name'))}', "
            f"pr.trigger_class='{q(p.get('trigger_class'))}', pr.approved=false, "
            f"pr.steps_json='{q(json.dumps(p.get('steps', [])))}'")
        self.graph.query(f"MERGE (h:Person {{name:'{q(taught_by)}'}})")
        self.graph.query(f"MATCH (pr:Protocol {{id:'{q(p['id'])}'}}), (h:Person {{name:'{q(taught_by)}'}}) "
                         f"MERGE (pr)-[:TAUGHT_BY]->(h)")
        self.graph.query(f"MATCH (pr:Protocol {{id:'{q(p['id'])}'}}), (ev:Event {{id:'{q(learned_from)}'}}) "
                         f"MERGE (pr)-[:LEARNED_FROM]->(ev)")
        self.graph.query(f"MATCH (pr:Protocol {{id:'{q(p['id'])}'}}), (t:TriggerClass {{name:'{q(p.get('trigger_class'))}'}}) "
                         f"MERGE (pr)-[:HANDLES]->(t)")
        return p

    def approve(self, pid, approver):
        p = super().approve(pid, approver)
        if p:
            q = self._q
            self.graph.query(f"MATCH (pr:Protocol {{id:'{q(pid)}'}}) SET pr.approved=true")
            self.graph.query(f"MERGE (h:Person {{name:'{q(approver)}'}})")
            self.graph.query(f"MATCH (pr:Protocol {{id:'{q(pid)}'}}), (h:Person {{name:'{q(approver)}'}}) "
                             f"MERGE (pr)-[:APPROVED_BY]->(h)")
        return p

    def record_use(self, pid, event_id, ok):
        rid = super().record_use(pid, event_id, ok)
        q = self._q
        self.graph.query(f"CREATE (r:Receipt {{id:'{q(rid)}', ok:{str(bool(ok)).lower()}}})")
        self.graph.query(f"MATCH (r:Receipt {{id:'{q(rid)}'}}), (pr:Protocol {{id:'{q(pid)}'}}) MERGE (r)-[:RAN]->(pr)")
        self.graph.query(f"MATCH (r:Receipt {{id:'{q(rid)}'}}), (ev:Event {{id:'{q(event_id)}'}}) MERGE (r)-[:ON]->(ev)")
        return rid

    def save_commitment(self, c):
        c = super().save_commitment(c)
        q = self._q
        self.graph.query(f"MERGE (cm:Commitment {{id:'{q(c['id'])}'}}) SET "
                         f"cm.promise='{q(c.get('promise', ''))}', cm.status='open', "
                         f"cm.deadline_days={int(c.get('deadline_days', 15))}")
        self.graph.query(f"MERGE (p:Contact {{name:'{q(c.get('person', ''))}'}})")
        self.graph.query(f"MATCH (cm:Commitment {{id:'{q(c['id'])}'}}), (p:Contact {{name:'{q(c.get('person', ''))}'}}) "
                         f"MERGE (cm)-[:PROMISED_TO]->(p)")
        if c.get("source_event"):
            self.graph.query(f"MATCH (cm:Commitment {{id:'{q(c['id'])}'}}), (ev:Event {{id:'{q(c['source_event'])}'}}) "
                             f"MERGE (cm)-[:DETECTED_IN]->(ev)")
        return c

    def update_commitment(self, cid, **fields):
        c = super().update_commitment(cid, **fields)
        if c:
            q = self._q
            sets = [f"cm.status='{q(c['status'])}'"]
            if c.get("booked_slot"):
                sets.append(f"cm.booked_slot='{q(c['booked_slot'])}'")
            self.graph.query(f"MATCH (cm:Commitment {{id:'{q(cid)}'}}) SET {', '.join(sets)}")
        return c


def make_store():
    if os.environ.get("MEMORY_BACKEND") == "falkor":
        return FalkorStore()
    return LocalStore()
