# Session A — RocketRide judgment / protocol pipes

Owns Guild distill → critic → arm → verify plus invoice protocol P-001 and classifiers for noise / important personal.

**Does not touch Session B files** (`P-FIND-SLOT`, `P-BOOK-HOLD`, `P-SEND-MESSAGE`, `P-FOLLOWUP-NUDGE`, `P-REPLAY-DAY`, `SESSION_B_PIPES.md`) or ingest/process/execute/keeper pipes.

## Env conventions (shared with process pipe)

| Variable | Use |
| -------- | --- |
| `${ROCKETRIDE_OPENAI_KEY}` | `llm_openai` |
| `${GUILD_API_KEY_ID}` / `${GUILD_API_KEY_SECRET}` | `tool_guild` |
| `${GUILD_WORKSPACE_OWNER}` / `${GUILD_WORKSPACE_NAME}` | Guild workspace |
| `${LASER_CONNECTION_STRING}` | `tool_laserdata_memory` |
| `${FALKOR_HOST}` / `${FALKOR_USERNAME}` / `${FALKOR_PASSWORD}` | `graph_falkordb` graph `personal_brain` |
| `${NOUS_CALLBACK_BASE}` | `nous_protocol` callbacks (P-001) |

Guild agents used: **`nous-distiller`**, **`nous-critic`** only.

---

## Catalog

### 1. `P-DISTILL-PROTOCOL.pipe`

- **Purpose:** Watched actions → parameterized Protocol stored **PENDING** (not armed).
- **Nodes:** `webhook` → `guardrails` → `agent_rocketride` + `llm_openai` / `memory_internal` / `tool_guild`(nous-distiller) / `graph_falkordb`(writes) / `tool_laserdata_memory` → `response_answers`
- **Example webhook:**

```json
{
  "correlation_id": "corr-distill-1",
  "event_id": "evt-3",
  "event": {
    "id": "evt-3",
    "trigger_class": "incoming_invoice",
    "subject": "Invoice #4417 — due Aug 17",
    "fields": { "from": "billing@acmedesign.co" }
  },
  "watched": [
    { "action": "forward", "params": { "to": "accounting@myfirm.com" } },
    { "action": "label", "params": { "name": "invoices" } },
    { "action": "archive", "params": {} }
  ]
}
```

### 2. `P-CRITIC-REVIEW.pipe`

- **Purpose:** Adversarial Guild critic; `APPROVE_ELIGIBLE` or `REJECTED`; still **not armed**.
- **Nodes:** `webhook` → `guardrails` → `agent_rocketride` + `llm_openai` / `memory_internal` / `graph_falkordb` / `tool_guild`(nous-critic) / `tool_laserdata_memory` → `response_answers`
- **Example webhook:**

```json
{
  "correlation_id": "corr-critic-1",
  "protocol_id": "P-001"
}
```

### 3. `P-001.pipe` (rewrite)

- **Purpose:** Armed invoice protocol executor via custom `nous_protocol`: **forward → label(invoices) → archive**.
- **Nodes:** `webhook` → `nous_protocol` → `response_text`
- **Notes:** `to` parameterized as `$to` (pass in webhook `inputs`); no vendor hardcoding; postcondition requires three `receipt_exists` checks.
- **Example webhook (text/JSON payload for nous_protocol):**

```json
{
  "run_id": "rr-demo-001",
  "event_id": "evt-5",
  "protocol_id": "P-001",
  "trigger_class": "incoming_invoice",
  "inputs": { "to": "accounting@myfirm.com" }
}
```

### 4. `P-APPROVE-ARM.pipe`

- **Purpose:** Human `{protocol_id, approved}` gate → FalkorDB **ARMED** + LaserData `nous:receipts`.
- **Nodes:** `webhook` → `guardrails` → `agent_rocketride` + `llm_openai` / `memory_internal` / `graph_falkordb` / `tool_laserdata_memory`(nous:receipts) → `response_answers`
- **Example webhook:**

```json
{
  "protocol_id": "P-001",
  "approved": true,
  "correlation_id": "corr-arm-1"
}
```

Reject example: `{ "protocol_id": "P-001", "approved": false }` → `{ "status": "rejected", "reason": "not_approved" }`.

### 5. `P-VERIFY-RECEIPTS.pipe`

- **Purpose:** Read-mostly receipt check against FalkorDB + LaserData.
- **Nodes:** `webhook` → `guardrails` → `agent_rocketride` + `llm_openai` / `memory_internal` / `graph_falkordb`(allow_writes:false) / `tool_laserdata_memory` → `response_answers`
- **Example webhook:**

```json
{
  "event_id": "evt-5",
  "protocol_id": "P-001",
  "correlation_id": "corr-verify-1",
  "expected_actions": ["forward", "label", "archive"]
}
```

### 6. `P-NOISE-FILTER.pipe`

- **Purpose:** `fyi_noise` → publish ignored classification; no commitments / no Guild.
- **Nodes:** `webhook` → `agent_rocketride` + `llm_openai` / `memory_internal` / `tool_laserdata_memory` → `response_answers`
- **Example webhook:**

```json
{
  "correlation_id": "corr-noise-1",
  "event_id": "evt-4",
  "trigger_class": "fyi_noise",
  "subject": "Your Monday briefing",
  "from": "newsletter@technews.io"
}
```

### 7. `P-IMPORTANT-PERSONAL.pipe`

- **Purpose:** Soft Commitment stub `awaiting_approval`; no auto book/send.
- **Nodes:** `webhook` → `guardrails` → `agent_rocketride` + `llm_openai` / `memory_internal` / `graph_falkordb` / `tool_laserdata_memory` → `response_answers`
- **Example webhook:**

```json
{
  "correlation_id": "corr-personal-1",
  "event_id": "evt-1",
  "trigger_class": "important_personal",
  "person": "Sam",
  "subject": "moving to London",
  "body": "Hey man — it's official, I'm moving to London."
}
```

---

## Structural validation checklist

Each Session A pipe has `version: 1`, a unique `project_id`, `components[]` with valid `provider` values, and wired `input` / `control` lanes matching the process/ingest pattern.
