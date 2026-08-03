# Session B — Motion / follow-through pipes

Owns **only** the RocketRide motion layer for the Nous prize: find slot → book hold → send message → follow-up nudge → replay day.

**Does not touch Session A files** (`P-INGEST-*`, `P-PROCESS-COMMITMENT`, `P-EXECUTE-ACTION`, `P-KEEPER`, `SESSION_A_PIPES.md`, distiller/critic agents, `server.py`, frontend, etc.). Complements `P-EXECUTE-ACTION` / `P-KEEPER`; replaces nothing.

## Pipe catalog

| Pipe | Path | Purpose |
|------|------|---------|
| Find slot | `pipes/P-FIND-SLOT.pipe` | Calendar read → propose free slot → FalkorDB `proposed_slot` + LaserData |
| Book hold | `pipes/P-BOOK-HOLD.pipe` | Approved hold → Guild Calendar `create_event` → receipts; mark `booked` |
| Send message | `pipes/P-SEND-MESSAGE.pipe` | Approved Gmail/Slack send → receipts (never books calendar) |
| Follow-up nudge | `pipes/P-FOLLOWUP-NUDGE.pipe` | Cron: due booked commitments → nudge send → receipts (idempotent) |
| Replay day | `pipes/P-REPLAY-DAY.pipe` | LaserData `nous:life-events` recall/republish from offset |

## Nodes used

Shared env (same as execute/calendar pipes): `${ROCKETRIDE_OPENAI_KEY}`, `${GUILD_*}`, `${LASER_CONNECTION_STRING}`, `${FALKOR_*}`; graph `personal_brain`.

| Pipe | Flow |
|------|------|
| **P-FIND-SLOT** | `webhook` → `agent_rocketride` + controls `llm_openai`, `memory_internal`, `tool_guild`(nous-calendar-reader), `graph_falkordb`, `tool_laserdata_memory`(nous:life-events) → `response_answers` |
| **P-BOOK-HOLD** | `webhook` → `guardrails` → `agent_rocketride` + controls `llm_openai`, `memory_internal`, `graph_falkordb`, `tool_guild`(nous-calendar-writer), `tool_laserdata_memory`(nous:receipts) → `response_answers` |
| **P-SEND-MESSAGE** | `webhook` → `guardrails` → `agent_rocketride` + controls `llm_openai`, `memory_internal`, `graph_falkordb`, `tool_guild`(nous-gmail-writer), `tool_guild`(nous-slack-writer), `tool_laserdata_memory`(nous:receipts) → `response_answers` |
| **P-FOLLOWUP-NUDGE** | `webhook` → `agent_rocketride` + controls `llm_openai`, `memory_internal`, `graph_falkordb`, both writers, `tool_laserdata_memory`(nous:receipts) → `response_answers` |
| **P-REPLAY-DAY** | `webhook` → `agent_rocketride` + controls `llm_openai`, `memory_internal`, `tool_laserdata_memory`(nous:life-events) → `response_answers` |

## Required Guild agents

Publish (new folders only; do not modify existing agents):

| Agent | Folder | Used by |
|-------|--------|---------|
| `nous-calendar-reader` | existing `integrations/guild/nous-calendar-reader` | P-FIND-SLOT |
| `nous-calendar-writer` | existing `integrations/guild/nous-calendar-writer` | P-BOOK-HOLD |
| `nous-gmail-writer` | **new** `integrations/guild/nous-gmail-writer` | P-SEND-MESSAGE, P-FOLLOWUP-NUDGE |
| `nous-slack-writer` | **new** `integrations/guild/nous-slack-writer` | P-SEND-MESSAGE, P-FOLLOWUP-NUDGE |

### Guild agent publish step (writers)

```powershell
cd integrations/guild/nous-gmail-writer
guild agent init --name nous-gmail-writer --template LLM
# ensure agent.ts matches this repo folder
guild agent save --message "v1" --wait --publish

cd ../nous-slack-writer
guild agent init --name nous-slack-writer --template LLM
guild agent save --message "v1" --wait --publish
```

Connect **Gmail** and **Slack** under Guild → Credentials before live sends.

## Example webhook payloads

### P-FIND-SLOT

```json
{
  "correlation_id": "corr-find-1",
  "commitment_id": "C-001",
  "person": "Sam",
  "window_start": "2026-08-15T14:00:00-07:00",
  "window_end": "2026-08-15T18:00:00-07:00",
  "activity": "visit"
}
```

Expected output shape: `{ "status": "slot_proposed", "proposed_slot": {...}, "conflicts": [], "correlation_id": "...", "commitment_id": "C-001" }`

### P-BOOK-HOLD

```json
{
  "commitment_id": "C-001",
  "approved": true,
  "correlation_id": "corr-book-1"
}
```

Input is **only** `commitment_id` + `approved:true` (+ optional `correlation_id`). Title/date from the browser are ignored; trusted proposal comes from FalkorDB.

Expected: `{ "status": "completed"|"failed"|"rejected", "external_id"?: "...", "correlation_id": "...", "commitment_id": "C-001" }`

### P-SEND-MESSAGE

```json
{
  "commitment_id": "C-001",
  "approved": true,
  "channel": "gmail",
  "to": "sam.k@gmail.com",
  "text": "I'm free Saturday 2–6 — booking time to see you.",
  "correlation_id": "corr-send-1"
}
```

Slack variant: `"channel": "slack", "to": "C01234567"`.

Expected: `{ "status": "sent"|"failed"|"rejected", "channel": "gmail"|"slack", "correlation_id": "...", "commitment_id": "C-001" }`

### P-FOLLOWUP-NUDGE

```json
{
  "correlation_id": "corr-nudge-1"
}
```

Or empty `{}` for cron-style.

Expected: `{ "status": "ok", "nudged": [...], "skipped": [...] }`

### P-REPLAY-DAY

```json
{
  "correlation_id": "corr-replay-1",
  "from_offset": 0,
  "limit": 20
}
```

Expected: `{ "status": "replayed", "count": N, "event_ids": [...], "correlation_id": "..." }`

## Safety notes

- **P-BOOK-HOLD** / **P-SEND-MESSAGE**: `guardrails` on browser approval payloads; send/book only when `approved === true`.
- **P-FIND-SLOT**: calendar **read only** (nous-calendar-reader). Never `create_event`.
- **P-BOOK-HOLD**: never fabricates `external_id`; failure → receipt, not `booked`.
- **P-REPLAY-DAY**: no Guild writes; no FalkorDB destructive deletes; no external Gmail/Slack/Calendar mutation.
- **P-FOLLOWUP-NUDGE**: skips if nudge receipt already exists.

## Env (copy from existing pipes)

```powershell
$env:ROCKETRIDE_OPENAI_KEY='...'
$env:GUILD_API_KEY_ID='...'
$env:GUILD_API_KEY_SECRET='...'
$env:GUILD_WORKSPACE_OWNER='ali.amjad52114'
$env:GUILD_WORKSPACE_NAME='...'
$env:LASER_CONNECTION_STRING='user:password@host:port'
$env:FALKOR_HOST='localhost'
$env:FALKOR_USERNAME=''
$env:FALKOR_PASSWORD=''
```
