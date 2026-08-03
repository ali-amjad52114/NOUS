# Nous

**A personal brain that keeps your promises — and every skill it learns ships as a RocketRide pipeline.**

You tell a friend "let's get dinner next week" and by Thursday it's gone. Nous doesn't forget. It listens to your life stream, catches the promises you make, works out who you meant and when it should happen, proposes a real time against your calendar, and books it after one approval. When something routine shows up instead — an invoice, a recurring chore — it watches you handle it once, distills your behavior into a typed protocol, and from then on executes that skill as a **RocketRide pipeline**.

```text
Life event → LaserData → FalkorDB memory → Guild judgment → human approval → RocketRide execution → receipts
```

Quick local check:

```powershell
& "C:\Users\aliam\AppData\Local\Programs\Python\Python312\python.exe" demo.py
& "C:\Users\aliam\AppData\Local\Programs\Python\Python312\python.exe" server.py
# → http://127.0.0.1:7200
```

```bash
python3 demo.py     # full arc, ends ALL CHECKS PASSED
python3 server.py   # UI on http://127.0.0.1:7200
```

---

## Why RocketRide is the product surface

Hackathon judges do not award “we called an LLM.” They award **systems that run on their engine**. Nous treats RocketRide as:

1. **Compilation target** — watched human handling becomes a Protocol, then a `.pipe`.
2. **Execution muscle** — approved protocols and promise workflows run on the RocketRide canvas/engine, not as silent Python.
3. **Observability proof** — every judged run should leave a RocketRide task trace (`rocketride://…`), not only a `fallback://` rehearsal path.
4. **Prize narrative** — “build the most with RocketRide”: many real pipelines, real nodes, real Guild/LaserData/Falkor tools on the control plane.

**CEO line:** *Your engine is our brain’s muscle — every skill it learns compiles into a RocketRide pipeline.*

### Canonical node pattern (v1)

Most prize pipes follow the same RocketRide shape:

```text
webhook
  → (optional) guardrails
  → agent_rocketride
       ├─ llm_openai          (control)
       ├─ memory_internal     (control)
       ├─ tool_guild          (control)  — specialist Guild agents
       ├─ tool_laserdata_memory (control)
       └─ graph_falkordb      (control)  — personal_brain
  → response_answers
```

Invoice execution also uses the custom **`nous_protocol`** filter (preconditions → ordered `/actions/execute` → verify) calling back into Nous at `${NOUS_CALLBACK_BASE}` (default `http://127.0.0.1:7200`).

### RocketRide pipe catalog

| Lane | Pipes | Job |
| ---- | ----- | --- |
| **Ingest** | `P-INGEST-GMAIL`, `P-INGEST-SLACK`, `P-INGEST-CALENDAR` | Guild readers → normalize → LaserData `nous:life-events` |
| **Commitments** | `P-PROCESS-COMMITMENT`, `P-PROMISE-KEPT` | Propose / keep a promise with critic + approval gate |
| **Slots & action** | `P-FIND-SLOT`, `P-BOOK-HOLD`, `P-SEND-MESSAGE`, `P-FOLLOWUP-NUDGE`, `P-EXECUTE-ACTION` | Calendar/message motion via Guild writers |
| **Judgment (Session A)** | `P-DISTILL-PROTOCOL`, `P-CRITIC-REVIEW`, `P-APPROVE-ARM`, `P-VERIFY-RECEIPTS` | Distill → critic → arm → verify |
| **Classifiers** | `P-NOISE-FILTER`, `P-IMPORTANT-PERSONAL` | Ignore noise; soft personal stubs |
| **Learned skills** | `P-001`, `P-KEEPER` | Invoice protocol & keep-a-promise protocol executors |
| **Replay** | `P-REPLAY-DAY` | Day-of-life replay from durable streams |

Catalog notes: `pipes/SESSION_A_PIPES.md`, `pipes/SESSION_B_PIPES.md`, `pipes/P-PROMISE-KEPT.md`, `pipes/GUILD_ROCKETRIDE.md`.

### RocketRide deep dive

**Skills compile into pipelines.** [`kit/pipegen.py`](kit/pipegen.py) turns approved protocols into portable `.pipe` files. Committed examples include [`pipes/P-001.pipe`](pipes/P-001.pipe) and [`pipes/P-KEEPER.pipe`](pipes/P-KEEPER.pipe), plus the full ingest/judgment/action catalog above.

**Custom RocketRide node.** [`integrations/rocketride/nodes/nous_protocol/`](integrations/rocketride/nodes/nous_protocol/) binds `$input` parameters, calls `/actions/preconditions`, executes steps through `/actions/execute` with stable step IDs, then `/actions/verify`.

**Strict SDK lifecycle with real traces.** [`integrations/rocketride_runner.py`](integrations/rocketride_runner.py) drives `ping` → `validate` → `use` (FLOW trace) → `send` → `terminate`. Strict `local`/`cloud` modes refuse silent fallback; rehearsal fallback labels itself `fallback://`.

**Idempotent by construction.** Replaying `(run_id, step_id)` returns the original receipt without acting twice.

```bash
python3 integrations/rocketride_smoke.py --evidence evidence/rocketride-smoke.json
python3 integrations/rocketride_live_demo.py --evidence evidence/rocketride-mvp.json
```

Runbook: [`integrations/rocketride/README.md`](integrations/rocketride/README.md).

### RocketRide env

| Variable | Role |
| -------- | ---- |
| `${ROCKETRIDE_OPENAI_KEY}` | `llm_openai` on agent pipes |
| `${GUILD_API_KEY_ID}` / `${GUILD_API_KEY_SECRET}` | `tool_guild` |
| `${GUILD_WORKSPACE_OWNER}` / `${GUILD_WORKSPACE_NAME}` | Guild workspace |
| `${LASER_CONNECTION_STRING}` | `tool_laserdata_memory` |
| `${FALKOR_HOST}` / `${FALKOR_USERNAME}` / `${FALKOR_PASSWORD}` | `graph_falkordb` → `personal_brain` |
| `${NOUS_CALLBACK_BASE}` | `nous_protocol` callbacks |
| `ROCKETRIDE_MODE` / `ROCKETRIDE_URI` / `ROCKETRIDE_APIKEY` | Python SDK runner |

---

## Sponsors (all load-bearing)

### RocketRide — the muscle (primary)

Runtime, canvas pipelines, traces, cloud deployability. Break it and the brain remembers but never moves.

### LaserData — the senses

Durable life-event and receipt streams. Namespaces: `nous:life-events`, `nous:receipts`. App publish: [`kit/laserdata.py`](kit/laserdata.py). Break it and the brain is deaf.

### FalkorDB — the memory

Life graph `personal_brain` (Event, Contact, Commitment, Protocol, Receipt, Person, Action). [`kit/memory.py`](kit/memory.py) LocalStore or `MEMORY_BACKEND=falkor`.

```bash
docker run -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest
MEMORY_BACKEND=falkor python3 server.py
```

```cypher
MATCH (c:Commitment)-[r]->(x) RETURN c, r, x
```

### Guild.ai — the judgment

- **nous-distiller** — watched session → typed Protocol  
- **nous-critic** — `APPROVE_ELIGIBLE` \| `REJECT`  
- Connector agents — Gmail/Slack/Calendar readers & writers  

Guild never arms anything; the human owner does. Sources: [`integrations/guild/`](integrations/guild/).

---

## What the demo proves

1. Invoice arrives → brain **watches** forward/label/archive.  
2. Distilled **P-001**, critic-reviewed, compiled to a RocketRide `.pipe`.  
3. Second invoice **before approval** → **refuses**.  
4. Approve once → autonomous handling + receipts.  
5. Promise flow: typed promise → slot → approve → book/send (RocketRide path).  
6. Memory survives restart / Falkor browser still shows the graph.

---

## Safety model

Refuse-first. Allowlisted actions only. Critic before human arm. RocketRide callbacks via `/actions/preconditions|execute|verify` with stable `run_id` / `step_id` dedupe. Secrets stay in gitignored `.env`.

---

## Repository map

```
server.py                     brain HTTP surface
demo.py                       headless ALL CHECKS PASSED
kit/                          brain, parse, memory, pipegen, distill, laserdata, feed
frontend/                     landing, app, console, graph
pipes/                        RocketRide pipelines + session catalogs
integrations/rocketride/      custom node, smoke, runbook
integrations/guild/           Distiller, Critic, connector agents
tests/                        RocketRide, Guild, pipegen suites
evidence/                     live session screenshots / IDs
```

## Tests

```bash
python3 demo.py
python3 -m unittest discover -s tests
```

## Team / disclosure

Built at Memory Meets Motion (Devnovate, Frontier Tower, San Francisco). AI coding assistants were used; sponsor integrations were exercised against live services where evidence is recorded.

> Nous is a personal brain that keeps your promises — **LaserData senses, FalkorDB remembers, Guild judges, RocketRide moves.**
