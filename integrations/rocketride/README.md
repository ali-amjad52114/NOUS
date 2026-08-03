# RocketRide integration

This folder connects the Nous brain to a running RocketRide engine. It contains the custom `nous_protocol` data-plane node, a smoke pipeline, and the runbook for the judged flow. The compiled skills themselves live in the top-level [`pipes/`](../../pipes/) folder.

## Product contract

Every approved protocol is compiled to `pipes/<protocol_id>.pipe`. The runner sends the engine exactly this payload:

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

Only `/actions/execute` mutates state. Every step has a stable `step_id`, and repeating a `(run_id, step_id)` pair returns the original receipt without acting twice.

## Five-minute smoke test

1. Confirm your RocketRide connection is up (local engine on `ws://localhost:5565`, or your editor's configured connection) and open `integrations/rocketride/smoke.pipe`.
2. Set `ROCKETRIDE_URI` to that connection. Set `ROCKETRIDE_APIKEY` only if the connection uses one.
3. Run the SDK lifecycle smoke:

```bash
python3 integrations/rocketride_smoke.py --evidence evidence/rocketride-smoke.json
```

Pass means `ping`, `validate`, `use`, `send`, a non-empty response, and `terminate` all complete against the same runtime your editor shows.

## Thirty-minute full hookup

1. Open `pipes/P-001.pipe` on the RocketRide canvas. Confirm the input, the Nous execution stage, and the response are connected, then run Validate.
2. Start Nous in strict local mode with a fresh memory path so the run is repeatable:

```bash
export GUILD_MODE=fallback
export ROCKETRIDE_MODE=local
export ROCKETRIDE_URI='<your RocketRide URI>'
export NOUS_CALLBACK_BASE=http://127.0.0.1:7200
export NOUS_MEMORY_PATH="$PWD/evidence/rocketride-mvp-memory.json"
python3 server.py
```

3. In a second terminal, drive the live server brain:

```bash
python3 integrations/rocketride_live_demo.py --evidence evidence/rocketride-mvp.json
```

4. Open `http://127.0.0.1:7200/state` next to the matching RocketRide task trace and follow one event ID across the event, the run, three action receipts, and the use receipt.

## Acceptance criteria

- The judged run uses `ROCKETRIDE_MODE=local` or `cloud`; no `fallback://` trace appears.
- RocketRide receives all five contract fields and returns a structured callback result containing a boolean `ok`.
- Preconditions reject unknown events, unarmed protocols, trigger mismatches, changed action lists, and non-allowlisted actions with non-2xx responses.
- Execute callbacks arrive in protocol order with stable step IDs and exact bound parameters.
- P-001 produces exactly `forward`, `label`, and `archive` receipts carrying the same RocketRide `run_id` and `protocol_id`.
- Replaying one `(run_id, step_id)` returns `duplicate: true` and does not add a receipt or increment the brain action count.
- Verify returns the action receipt IDs plus a successful use receipt, and the matching task is visible on the engine.
- Invalid validation or unstructured engine output fails visibly; strict mode never silently invokes the deterministic fallback.
