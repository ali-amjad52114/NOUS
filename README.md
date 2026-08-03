# 🧠 Nous

**A personal brain that keeps your promises.**

You tell a friend "let's get dinner next week" and by Thursday it's gone. Nous doesn't forget. It listens to your life stream, catches the promises you make, works out who you meant and when it should happen, proposes a real time against your calendar, and books it after one approval. When something routine shows up instead, an invoice, a recurring chore, it watches you handle it once, distills your behavior into a typed protocol, and from then on executes that skill as a **RocketRide pipeline**.

The core is pure Python stdlib with zero dependencies, so verifying it takes one minute:

```bash
python3 demo.py     # the full arc, ends with ALL CHECKS PASSED
python3 server.py   # the same brain behind a UI on http://127.0.0.1:7200
```

## What the demo proves

1. An invoice arrives. The brain has never seen one, so it **watches** the owner handle it: forward, label, archive.
2. The watched actions are distilled into **Protocol P-001**, reviewed by a safety critic, and compiled into [`pipes/P-001.pipe`](pipes/P-001.pipe). The brain emits a RocketRide pipeline from watching a human work.
3. A second invoice from a different vendor arrives **before approval**. The brain **refuses to act**. Nothing runs without the owner's sign-off.
4. The owner approves once. The refused queue drains, and a third vendor is handled autonomously with a receipt citing the protocol it was taught.
5. Final scoreboard: owner 3 actions, brain 6. The memory survives a restart.

The same brain also handles the promise flow end to end: type "i wanna meet with kevin next week for dinner" on the landing page and it resolves the person, the activity, and the window, proposes a dated slot, and books it on approval.

## Architecture

```
                     your life stream
                    (LaserData / Iggy)
                            |
                            v
                the brain  (server.py + kit/)
        parse promises . watch . refuse . learn . book
             |                              |
             v                              v
     memory graph                distiller + safety critic
      (FalkorDB)                        (Guild.ai)
                                            |
                                            v
                                  human approval gate
                                            |
                                            v
                            kit/pipegen.py compiles the skill
                                            |
                                            v
                          RocketRide engine runs the pipeline
                                            |
                                            v
                      POST /actions/* callbacks into the brain
                        (allowlisted, verified, receipted)
```

The inversion that matters: once a skill is approved, **the app does not execute it. The RocketRide engine does.** The brain only exposes guarded callback endpoints and keeps the receipts.

## RocketRide, the execution engine

RocketRide is the deepest integration in this repo. It is not a demo step, it is the runtime for every skill the brain learns.

**Skills compile into pipelines.** [`kit/pipegen.py`](kit/pipegen.py) turns every approved protocol into a portable pipeline definition. Two are committed: [`pipes/P-001.pipe`](pipes/P-001.pipe) (the learned invoice skill) and [`pipes/P-KEEPER.pipe`](pipes/P-KEEPER.pipe) (the promise keeper). Each pipeline chains a trigger, a precondition check, one node per learned step, and a postcondition verify.

**A custom RocketRide node.** [`integrations/rocketride/nodes/nous_protocol/`](integrations/rocketride/nodes/nous_protocol/) is a data-plane node built against the RocketRide node SDK (`rocketlib`). It binds `$input` parameters, calls the brain's `/actions/preconditions` gate, executes each step through `/actions/execute` with stable step IDs, then confirms the postcondition through `/actions/verify`. Failures return structured errors instead of half-finished work.

**Strict SDK lifecycle with real traces.** [`integrations/rocketride_runner.py`](integrations/rocketride_runner.py) drives the full RocketRide client lifecycle: `ping`, `validate`, `use` with `FLOW` trace level, `send`, `terminate`. Every run carries a `rocketride://task/<token>` trace reference, so a judged run maps to a visible task trace on the engine. Strict `local` and `cloud` modes refuse to fall back silently; the deterministic fallback exists only for rehearsal and labels itself.

**Idempotent by construction.** Replaying a `(run_id, step_id)` pair returns the original receipt without acting twice, so a retried pipeline never double-executes a side effect.

**Try it yourself:**

```bash
python3 integrations/rocketride_smoke.py --evidence evidence/rocketride-smoke.json
python3 integrations/rocketride_live_demo.py --evidence evidence/rocketride-mvp.json
```

The full runbook and acceptance criteria live in [`integrations/rocketride/README.md`](integrations/rocketride/README.md).

## FalkorDB, the memory

Every person, promise, protocol, and receipt lives in a graph. [`kit/memory.py`](kit/memory.py) ships two interchangeable stores: a zero-dependency local store, and a FalkorDB store that mirrors every write as Cypher.

```bash
docker run -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest
MEMORY_BACKEND=falkor python3 server.py
```

Open the FalkorDB browser at `http://localhost:3000` (graph `personal_brain`) and watch memory grow while you use the app. A good starting query:

```cypher
MATCH (c:Commitment)-[r]->(x) RETURN c, r, x
```

Screenshots of live graphs are in [`evidence/`](evidence/).

## Guild.ai, the judgment

Two typed Guild agents stand between watching and acting, both published to a real Guild workspace with IDs recorded in [`evidence/guild-session-3.md`](evidence/guild-session-3.md):

* **nous-distiller** turns a watched event plus action receipts into a typed protocol: trigger class, steps, preconditions, a verifiable postcondition.
* **nous-critic** reviews that protocol against policy and returns `APPROVE_ELIGIBLE` or `REJECT` with findings. In our recorded sessions it rejected a non-allowlisted `delete` action, a hardcoded vendor identity, and a missing postcondition.

Guild never arms anything. A `REJECT` can never be approved, an `APPROVE_ELIGIBLE` still requires the human owner to click Approve, and if either agent times out or returns an invalid schema, Nous fails closed and persists nothing. Sources, fixtures, and the runbook are in [`integrations/guild/`](integrations/guild/), covered by 11 integration tests.

## LaserData, the senses

Every event the brain ingests is published to a Laser Stack stream in real time by [`kit/laserdata.py`](kit/laserdata.py), a failure-safe publisher that redacts credentials and never blocks the brain if the stream is down. [`integrations/replay_laserdata.py`](integrations/replay_laserdata.py) replays a captured stream back through the brain, and deployment screenshots are in [`evidence/`](evidence/).

## The safety model

Nous is built refuse-first. Untrained event classes are watched, never guessed at. Actions are allowlisted and typed. The critic reviews every distilled protocol before it can even be offered for approval. The human owner is the only party who can arm a skill, and every autonomous action leaves a receipt naming the protocol and the run that produced it.

## Repository map

```
server.py                     the brain's HTTP surface (stdlib only)
demo.py                       headless full-arc check, ends ALL CHECKS PASSED
kit/
  brain.py                    ingest, watch, refuse, learn, book
  parse.py                    deterministic promise parser (who, what, when)
  memory.py                   graph memory: local store + FalkorDB mirror
  pipegen.py                  compiles approved protocols into .pipe files
  distill.py                  distiller + critic roles
  laserdata.py                failure-safe Laser Stack publisher
  feed.py                     the demo life stream
frontend/                     landing page, the brain UI, power console
pipes/                        compiled RocketRide pipelines (P-001, P-KEEPER)
integrations/
  rocketride/                 custom node, smoke pipe, runbook
  rocketride_runner.py        strict SDK lifecycle runner
  guild/                      published agent sources, fixtures, runbook
tests/                        RocketRide, Guild, and pipegen test suites
evidence/                     screenshots and session IDs from live services
```

## Tests

```bash
python3 demo.py                          # ALL CHECKS PASSED
python3 -m unittest discover -s tests    # RocketRide callbacks, Guild contracts, pipegen
```

## Team

Built in one day at Memory Meets Motion (Devnovate, Frontier Tower, San Francisco). AI coding assistants were used throughout the build; every sponsor integration was exercised against the real running service, and the evidence folder holds the session IDs and screenshots to prove it.
