# Cursor RocketRide hookup

Scope: connect the already-working Cursor RocketRide session to Nous. This
handoff does not install, repair, deploy, or configure the platform.

## Product contract

The approved protocol is compiled to `pipes/<protocol_id>.pipe`. The runner
sends exactly:

```json
{
  "run_id": "rr-...",
  "event_id": "evt-...",
  "protocol_id": "P-001",
  "trigger_class": "incoming_invoice",
  "inputs": {}
}
```

RocketRide owns the runtime sequence:

`preconditions -> ordered execute callbacks -> verify -> structured response`

Only `/actions/execute` mutates state. Every step has a stable `step_id`, and
repeating `(run_id, step_id)` returns the original receipt without acting twice.

## Five-minute smoke test

1. In Cursor, confirm the existing RocketRide connection is green and open
   `integrations/rocketride/smoke.pipe`.
2. Set `ROCKETRIDE_URI` to that existing local connection. Set
   `ROCKETRIDE_APIKEY` only if the Cursor connection uses one.
3. Run the SDK lifecycle smoke:

```powershell
python integrations/rocketride_smoke.py --evidence evidence/rocketride-smoke.json
```

Pass means `ping`, `validate`, `use`, `send`, a non-empty response, and
`terminate` all complete against the same runtime Cursor shows.

## Thirty-minute MVP hookup

1. In Cursor, open `pipes/P-001.pipe`. Confirm the input, Nous execution stage,
   and response are connected, then run Validate.
2. Start Nous in strict local mode. Use a new memory path so the demo is
   repeatable:

```powershell
$env:GUILD_MODE='fallback'
$env:ROCKETRIDE_MODE='local'
$env:ROCKETRIDE_URI='<the existing Cursor RocketRide URI>'
$env:NOUS_CALLBACK_BASE='http://127.0.0.1:7200'
$env:NOUS_MEMORY_PATH="$PWD/evidence/rocketride-mvp-memory.json"
python server.py
```

3. In a second terminal, drive the real server Brain:

```powershell
python integrations/rocketride_live_demo.py --evidence evidence/rocketride-mvp.json
```

4. Open `http://127.0.0.1:7200/state` and the matching RocketRide task trace.
   Follow one event ID across the event, run, three action receipts, and use
   receipt.

## Acceptance criteria

- The judged run uses `ROCKETRIDE_MODE=local`; no `fallback://` trace appears.
- RocketRide receives all five contract fields and returns a structured
  callback result containing boolean `ok`.
- Preconditions reject unknown events, unarmed protocols, trigger mismatch,
  changed action lists, and non-allowlisted actions with non-2xx responses.
- Execute callbacks arrive in protocol order with stable step IDs and exact
  bound parameters.
- P-001 produces exactly `forward`, `label`, and `archive` receipts carrying
  the same RocketRide `run_id` and `protocol_id`.
- Replaying one `(run_id, step_id)` returns `duplicate: true` and does not add a
  receipt or increment the brain action count.
- Verify returns the action receipt IDs plus a successful use receipt, and the
  matching task is visible in Cursor.
- Invalid validation or unstructured engine output fails visibly; strict mode
  never silently invokes the deterministic fallback.
