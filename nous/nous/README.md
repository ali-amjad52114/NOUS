# 🧠 Nous — a personal brain that keeps your promises

**A brain that learns your moves, not just your facts.** It watches you handle
something once, compiles your handling into a *Protocol* (Ali's word — keep it),
and from then on executes it autonomously — **as a RocketRide pipeline.**

Built with AI assistance (disclose in the submission). Zero dependencies —
pure Python stdlib. Verify it in 30 seconds:

```bash
python3 demo.py     # full arc: watch → distill → REFUSE pre-approval →
                    # approve → autonomous on two new vendors → persistence
python3 server.py   # same brain behind YOUR agreed endpoints on :7200
```

## The demo arc (protect these beats, cut anything else)

1. Invoice arrives → brain has never seen one → **watches you** handle it
2. **Protocol P-001 appears** + critic review + `pipes/P-001.pipe` is emitted —
   the brain literally compiled a RocketRide pipeline from watching you
3. Second invoice (different vendor) BEFORE approval → **it refuses** ✋
4. You approve once → queue drains + third vendor handled autonomously,
   citing "the protocol Abhinav taught me" + receipt
5. Scoreboard: *you: 3 actions · brain: 6* — and it survives a restart

## Person-by-person wiring (matches your FarmGuild contract)

**Person 1 — feed + UI:** drive `POST /events` with `kit/feed.py` events (or
your own), render `GET /state` (log, scoreboard, pending approvals), one
Approve button → `POST /approve`. Watch-mode buttons → `POST /watch/action`,
`POST /watch/done`.

**Person 2 — LaserData + FalkorDB:** `kit/feed.py::publish` is the LaserData
hook (one TODO line). `kit/memory.py` has the full graph — LocalStore works
now; `MEMORY_BACKEND=falkor` + docker + `pip install falkordb` flips on the
real graph, browser at :3000. Judge query:
`MATCH (p:Protocol)-[r]->(x) RETURN p, r, x`

**Person 3 — Guild + RocketRide (the prize lane):**
- Guild: publish two agents from `kit/distill.py`'s roles — Distiller + Safety
  Critic (`guild agent init --template LLM`, paste the prompts, `guild agent
  save --publish`). Install a Hub agent too. The approve step is the HITL beat.
- RocketRide: `kit/pipegen.py` emits a `.pipe` per learned protocol. Load one
  on the engine (docker :5565), recreate it on the VS Code canvas WITH A
  ROCKETRIDE MENTOR (their node schema is canonical — this is also face time
  with the people who pick their prize), deploy to RocketRide Cloud with the
  Discord promo code, keep the observability trace open for judges.
  The pipes call back into `POST /actions/execute` — the engine drives the
  motion, not the app.

## The CEO pitch line

"You said this morning you'd buy a personal brain. Here it is — and every
skill it learns compiles into a RocketRide pipeline. Your engine is the
compilation target of our brain. Watch it learn its first one."

Nebius upgrade (optional): set NEBIUS_API_KEY/NEBIUS_MODEL — `kit/distill.py`
auto-upgrades distiller prose; deterministic path stays as the safety net.
