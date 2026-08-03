# Problem: Keep One Promise (end-to-end)

## The human moment

Sam is moving to London. You wrote: *"I'm coming to see you before you go, I promise."*

Every other Nous pipe handles a **slice** of that moment (ingest, process, find-slot, book, send, nudge). Judges never see the full defense of a promise as **one RocketRide run**.

## The problem this pipe solves

**Given** a life-event id (already in LaserData) and an optional human approval flag, **keep the promise** without skipping memory, judgment, or proof:

1. **Sense** — recall the event from LaserData; refuse duplicates via FalkorDB
2. **Propose** — find a free calendar slot (Guild reader); draft a commitment + message
3. **Judge** — Guild Critic must accept before anything is approval-ready
4. **Gate** — mid-pipe guardrails: no calendar/message writes unless `approved === true`
5. **Act** — book the hold (Guild calendar writer) + send Sam the message (Guild Gmail writer)
6. **Prove** — dual receipts in LaserData `nous:receipts` + FalkorDB `(:Action)-[:PRODUCED]->(:Receipt)`; verify book + send both exist or fail closed

Stop cleanly at the first failed stage. Never fabricate `external_id`. Never trust browser title/date — only Falkor/Laser trust store + Guild tools.

## Why this pipe (not complexity theater)

| Existing pipes | This pipe |
|---|---|
| One agent each | **Three staged agents** chained on the canvas |
| One Guild agent | **Reader + Critic + Calendar writer + Gmail writer** |
| One LaserData namespace | **life-events + receipts** |
| Approve then execute elsewhere | **Sense → plan → approve gate → act → prove in one trace** |

Artifact: `pipes/P-PROMISE-KEPT.pipe` (15 nodes).

## Demo webhook

```json
{
  "correlation_id": "corr-promise-kept-1",
  "event_id": "evt-2",
  "approved": true,
  "window_start": "2026-08-14T00:00:00Z",
  "window_end": "2026-08-17T23:59:59Z"
}
```

Without `"approved": true`, the pipe must stop after plan/critic with `status: "awaiting_approval"` and perform zero external writes.
