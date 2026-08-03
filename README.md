# Nous

**A personal brain that keeps your promises — and every skill it learns ships as a RocketRide pipeline.**

Nous watches your life stream (Gmail, Slack, calendar), catches intentions you make in passing, remembers them as commitments, waits for human approval, then **moves**. Motion is not a Python side-effect buried in the app. Motion is a **RocketRide `.pipe`**: traced, deployable, judge-visible.

```text
Life event → LaserData → FalkorDB memory → Guild judgment → human approval → RocketRide execution → receipts
```

Quick local check (stdlib brain path):

```powershell
& "C:\Users\aliam\AppData\Local\Programs\Python\Python312\python.exe" demo.py
& "C:\Users\aliam\AppData\Local\Programs\Python\Python312\python.exe" server.py
# → http://127.0.0.1:7200
```

---

## Why RocketRide is the product surface

Hackathon judges do not award “we called an LLM.” They award **systems that run on their engine**. Nous treats RocketRide as:

1. **Compilation target** — watched human handling becomes a Protocol, then a `.pipe`.
2. **Execution muscle** — approved protocols and promise workflows run on the RocketRide canvas/engine, not as silent Python.
3. **Observability proof** — every judged run should leave a RocketRide task trace (`rocketride://…`), not only a `fallback://` rehearsal path.
4. **Prize narrative** — “build the most with RocketRide”: many real pipelines, real nodes, real Guild/LaserData/Falkor tools on the control plane.

### Canonical node pattern (v1)

Most prize pipes follow the same RocketRide shape used by ingest/process:

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

### RocketRide pipe catalog (high level)

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

### RocketRide env (orchestration pipes)

| Variable | Role |
| -------- | ---- |
| `${ROCKETRIDE_OPENAI_KEY}` | `llm_openai` on agent pipes |
| `${GUILD_API_KEY_ID}` / `${GUILD_API_KEY_SECRET}` | `tool_guild` |
| `${GUILD_WORKSPACE_OWNER}` / `${GUILD_WORKSPACE_NAME}` | Guild workspace |
| `${LASER_CONNECTION_STRING}` | `tool_laserdata_memory` |
| `${FALKOR_HOST}` / `${FALKOR_USERNAME}` / `${FALKOR_PASSWORD}` | `graph_falkordb` → graph `personal_brain` |
| `${NOUS_CALLBACK_BASE}` | `nous_protocol` HTTP callbacks |
| `ROCKETRIDE_MODE` / `ROCKETRIDE_URI` / `ROCKETRIDE_APIKEY` | Python SDK runner (`local` \| `cloud` \| `fallback`) |

SDK runner: `integrations/rocketride_runner.py` · smoke: `integrations/rocketride_smoke.py` · custom node: `integrations/rocketride/nodes/nous_protocol/`.

**CEO line:** *Your engine is our brain’s muscle — every skill it learns compiles into a RocketRide pipeline.*

---

## Sponsors (all load-bearing)

### 1. RocketRide — the muscle (primary)

- **What it owns:** Runtime sequence, canvas pipelines, traces, cloud deployability.
- **What Nous builds on it:** Dozens of `.pipe` files; `agent_rocketride` orchestrators; Guild/LaserData/Falkor as **tools on the RocketRide control plane**; custom `nous_protocol` for allowlisted, receipted steps.
- **Proof judges should see:** A non-`fallback://` task trace for P-001 or `P-PROMISE-KEPT`, canvas open, Cloud deploy if available.
- **Break it and…** the brain remembers but never moves.

### 2. LaserData — the senses

- **What it owns:** Durable life-event and receipt streams (Apache Iggy–based cloud).
- **Namespaces:** `nous:life-events`, `nous:receipts` (and protocol summaries as needed).
- **In pipes:** `tool_laserdata_memory` with `${LASER_CONNECTION_STRING}`.
- **In app:** `kit/laserdata.py` / `LASERDATA_URL` for optional publish from the Python brain.
- **Break it and…** the brain is deaf — no durable stream, no replay story.

### 3. FalkorDB — the memory

- **What it owns:** The life graph browsable for judges.
- **Graph:** `personal_brain` — Event, Contact, Commitment, Protocol, Receipt, Person, Action; edges like `PROMISED_TO`, `LEARNED_FROM`, `APPROVED_BY`, `RAN` / `ON` / `PRODUCED`.
- **In pipes:** `graph_falkordb` (writes for distill/arm/commitments; read-mostly for verify).
- **In app:** `kit/memory.py` — `LocalStore` by default; `MEMORY_BACKEND=falkor` for live graph.
- **Judge query:** `MATCH (p:Protocol)-[r]->(x) RETURN p, r, x` (or Commitment-centric variants).
- **Break it and…** the brain has amnesia across the session.

### 4. Guild.ai — the judgment

- **What it owns:** Specialist agents with typed I/O and human-final authority.
- **Core agents:** `nous-distiller` (compile watched sessions → Protocol), `nous-critic` (adversarial `APPROVE_ELIGIBLE` \| `REJECT`).
- **Connector agents (ingest/act):** Gmail/Slack/Calendar readers & writers under `integrations/guild/`.
- **In pipes:** `tool_guild` pointed at the agent name; RocketRide waits on session results.
- **In app:** `integrations/guild/guild_runner.py` (`GUILD_MODE=live|fallback`).
- **Break it and…** the brain acts unreviewed — or you lose the refusal/HITL story.

### Sponsor flow (one picture)

```text
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│  Gmail etc. │────▶│  LaserData   │────▶│  FalkorDB  │
│  (Guild R/W)│     │  life-events │     │  memory    │
└─────────────┘     └──────────────┘     └─────▲──────┘
                                               │
                    ┌──────────────┐           │
                    │   Guild.ai   │───────────┤ distill / critic
                    │  Distiller + │           │
                    │    Critic    │           │
                    └──────┬───────┘           │
                           │ HITL approve      │
                    ┌──────▼───────┐           │
                    │  RocketRide  │───────────┘ arm / execute / receipts
                    │  .pipe runs  │──────────────────▶ LaserData receipts
                    └──────────────┘
```

---

## Demo story (protect these beats)

1. **Promise** — Sam’s news → you promise to visit → commitment + slot → approve → book + message (+ follow-up path on RocketRide).
2. **Learn** — First invoice → watch you → Distiller → Critic → `.pipe` emitted / pending.
3. **Refuse** — Second invoice before arm → **refuses**.
4. **Arm & run** — Approve once → autonomous handling with receipts and a RocketRide trace.
5. **Remember** — Restart / Falkor browser still shows Protocol + Commitment.

Headless rehearsal: `demo.py` should print `ALL CHECKS PASSED` (fallback-safe). Judged demo: prefer `ROCKETRIDE_MODE=local|cloud` and `GUILD_MODE=live` with real traces.

---

## Repo map

| Path | Role |
| ---- | ---- |
| `server.py` | HTTP brain API + frontend |
| `kit/brain.py` | Promise + protocol loops |
| `kit/pipegen.py` | Protocol → RocketRide `.pipe` |
| `kit/memory.py` | LocalStore / FalkorStore |
| `kit/laserdata.py` | Optional stream publish |
| `integrations/rocketride_*` | SDK runner, smoke, live demo |
| `integrations/guild/` | Distiller, Critic, connector agents |
| `pipes/` | All RocketRide pipelines + session catalogs |
| `frontend/` | Landing, app, console, graph |
| `demo.py` | Headless stage arc |

---

## Human approval boundary

- Protocols are **not armed** until a human approves (`P-APPROVE-ARM` / `/approve`) after Guild `APPROVE_ELIGIBLE`.
- Promises book/send only after explicit commitment approval (and promise pipes must stop at `awaiting_approval` when `approved !== true`).
- Allowlisted actions only: `forward`, `label`, `archive`, `reply`, `book`, `send_message`.
- RocketRide execute callbacks hit Nous `/actions/preconditions|execute|verify` with stable `run_id` / `step_id` dedupe.

---

## Runbook (sponsors on)

1. **Nous:** `server.py` on `:7200`.
2. **RocketRide:** local/canvas runtime or Cloud; load pipes; set `ROCKETRIDE_*` and OpenAI key for agent pipes.
3. **Guild:** published agents + API trigger credentials in env.
4. **LaserData:** connection string → `${LASER_CONNECTION_STRING}` / `LASERDATA_URL`.
5. **FalkorDB:** docker + credentials → `${FALKOR_*}`; optional UI `:3000`.

Secrets stay in gitignored `.env` — never commit keys.

---

## Disclosure

Built with AI assistance — disclose on submission.

---

## One line for the booth

> Nous is a personal brain that keeps your promises — **LaserData senses, FalkorDB remembers, Guild judges, RocketRide moves.**
