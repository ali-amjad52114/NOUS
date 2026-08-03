# Nous — Session 2 and Session 3 integration plan

This plan gives each session one platform and one proof. Phase 0 is a hard
smoke-test gate; do not build on an SDK, CLI, credential, or pipeline format
that has not passed it.

## Shared outcome

The final demo path must be:

`Nous event -> Guild distills and critiques -> human arms protocol -> RocketRide runs it -> Nous receipts and verifies it`

The sponsor products must be in the runtime path. A successful login, API-key
call, generated file, or open dashboard alone does not count as integration.

Shared rules:

- Begin and end with `python demo.py` printing `ALL CHECKS PASSED`.
- Never hardcode secrets. Use the platform login or environment variables.
- Put screenshots, trace IDs, session IDs, and command output in `evidence/`.
- Use a public callback base URL for cloud runs; RocketRide Cloud and Guild
  cannot call `127.0.0.1` on the demo laptop.
- Preserve the deterministic local path as a fallback, but run the judged demo
  in strict integration mode so a silent fallback cannot create fake evidence.

---

## Session 2 — RocketRide owns execution

### Definition of done

An approved Nous protocol is compiled into a valid RocketRide pipeline. Nous
dispatches a real event to that pipeline through the Python SDK. RocketRide
calls the three Nous action hooks in order, and the final result is visible as
both Nous receipts and a RocketRide trace. The same pipeline runs locally and
on RocketRide Cloud.

### Phase 0 — smoke test (20–30 minutes, hard gate)

1. Establish the local baseline:
   - Run `python demo.py` and save the green output.
   - Start `python server.py`; verify `GET /state` returns JSON.
   - POST one known event from `kit/feed.py` and confirm it appears in state.
2. Establish RocketRide independently:
   - Install the current `rocketride` Python package and VS Code extension.
   - Start the local runtime on `ws://localhost:5565` using the current official
     quickstart or the booth mentor's canonical command.
   - Build a tiny pass-through pipeline on the visual canvas. Do not start with
     a generated Nous pipe.
3. Write `integrations/rocketride_smoke.py` using the documented lifecycle:
   - connect with `RocketRideClient`;
   - `ping()`;
   - `validate()` the pass-through pipeline;
   - `use(filepath=...)`, `send(...)`, assert a response, then `terminate()`.
4. Repeat the smoke once against RocketRide Cloud with
   `ROCKETRIDE_URI=https://cloud.rocketride.ai` and `ROCKETRIDE_APIKEY`.
5. Save the local and cloud outputs plus one trace screenshot.

**Phase 0 exit gate:** local and cloud can connect, validate, use, send, return
a result, and terminate. If this fails, fix credentials/runtime/schema with a
mentor before touching Nous.

### MVP build (75–100 minutes)

#### 1. Make the callback contract real

Define one payload used by the dispatcher, pipeline, and callbacks:

```json
{
  "run_id": "rr-...",
  "event_id": "evt-...",
  "protocol_id": "P-001",
  "trigger_class": "incoming_invoice",
  "inputs": {}
}
```

Fix `kit/pipegen.py` so every generated action body includes `event_id`,
`protocol`, `run_id`, and a stable `step_id`. Today the generated pipes omit
`event_id`, although `/actions/execute` requires it.

Make the callback base configurable with `NOUS_CALLBACK_BASE`. Use localhost
for the local engine and a tunnel/deployed URL for Cloud.

#### 2. Replace the placeholder safety hooks

- `/actions/preconditions` must check that the event exists, the protocol
  exists and is armed, the event trigger class matches, and every planned
  action is allowlisted. Return structured checks and a non-2xx response on
  failure.
- `/actions/execute` must reject unarmed/mismatched protocols and deduplicate
  `(run_id, step_id)` so a retry cannot execute an action twice. Each accepted
  step creates a receipt carrying the RocketRide run ID.
- `/actions/verify` must evaluate the selected protocol's postcondition:
  P-001 is forwarded + labeled + archived; P-KEEPER is booked + message sent.
  Return the receipt IDs and verification result.

Add direct API tests for the happy path, unapproved protocol, wrong trigger,
non-allowlisted action, unknown event, and duplicate step.

#### 3. Compile a canonical pipeline

- Rebuild P-001 on the RocketRide canvas with canonical nodes and export it.
- Use that export as the schema reference for `pipegen.py`; do not guess the
  current `.pipe` schema.
- Flow: input -> parse payload -> preconditions -> action steps -> verify ->
  structured output.
- Use RocketRide variable bindings for values from the input payload. Do not
  hardcode `evt-2`, a vendor, person, slot, or callback host.
- Run RocketRide's validator on every generated pipe before execution.

#### 4. Put RocketRide in the application path

Create `integrations/rocketride_runner.py` with one entry point:

`run_protocol(pipe_path, event_payload) -> {run_id, ok, output, trace_ref}`

Wire the approved autonomous P-001 path to this runner. The runner sends the
event JSON to RocketRide; it must not execute the invoice steps itself. The
only mutations happen when RocketRide calls `/actions/execute`.

After P-001 is green, wire P-KEEPER through the same runner so the headline
promise demo also uses RocketRide. Keep `ROCKETRIDE_MODE=local|cloud|fallback`;
use `local` or `cloud` for evidence, and make failures visible in strict mode.

#### 5. Prove local and cloud parity

- Local: ingest a new approved invoice; capture SDK output, three callback
  requests, receipts, verification, and the RocketRide trace.
- Cloud: expose the Nous callback server through the agreed tunnel/deployment,
  publish the same validated artifact, send a different invoice, and capture
  the same evidence.
- Re-run one duplicate `step_id` and show that no second receipt is created.

### Session 2 handoff

- Files: runner, smoke script, canonical/generated pipes, callback tests.
- Evidence: local trace, cloud trace, Nous receipts, pipeline canvas.
- Record: exact SDK version, runtime command, callback URL strategy, Cloud
  deployment/project/version IDs, and the one-command demo invocation.

Do not spend MVP time on cron, extra AI nodes, multiple environments, or a
general workflow editor. One end-to-end pipeline with real safety, execution,
verification, and traceability is the prize-worthy proof.

---

## Session 3 — Guild owns judgment

### Definition of done

The watched human actions are sent to the published Nous Distiller agent. Its
typed protocol output is passed to the published Safety Critic. The critic's
structured verdict is stored with Guild session/version provenance and gates
whether the human is allowed to arm the protocol. The Guild session visibly
contains the actual P-001 used by the demo.

### Phase 0 — smoke test (20–30 minutes, hard gate)

1. Run `node --version` (18+), install `@guildai/cli`, then run:
   - `guild auth login`
   - `guild auth status`
   - `guild workspace select`
   - `guild doctor`
2. In a disposable folder, initialize a minimal LLM agent, save it, and run
   `guild agent test --ephemeral` with `ping`. Confirm a response and a visible
   session in the selected workspace.
3. Run `guild agent save --message "phase-0 smoke" --wait`; confirm validation.
   Publishing the disposable agent is optional; validation and a session are
   required.
4. Save the CLI output and session screenshot.

**Phase 0 exit gate:** authentication, workspace selection, agent build,
ephemeral execution, validation, and session logging all work. If any fails,
resolve that before editing the Nous agents.

### MVP build (75–100 minutes)

#### 1. Give both agents strict contracts

Create separate Guild project folders for `nous-distiller` and `nous-critic`.
Use the existing prompts as policy, but add typed JSON input/output schemas.

Distiller input:

- source event ID, trigger class, safe event fields;
- ordered watched receipts with action and params;
- allowed-action list and owner ID.

Distiller output:

- name, trigger class, typed preconditions, parameterized steps,
  postcondition, and risk.

Critic input is the exact distiller output plus policy. Critic output is:

- `verdict: APPROVE_ELIGIBLE | REJECT`;
- numbered findings, residual risk, and normalized checks.

Fail closed on invalid JSON, missing fields, non-allowlisted actions,
hardcoded one-off values, or vague postconditions. Use one-shot behavior for
deterministic machine calls; reserve multi-turn for the visible review session.

#### 2. Test adversarially before publishing

Run both agents with fixtures committed under `integrations/guild/fixtures/`:

- valid invoice demonstration;
- forbidden action;
- hardcoded vendor-specific protocol;
- missing approval precondition;
- unverifiable postcondition;
- malformed output.

The good fixture must become approve-eligible. Every unsafe fixture must be
rejected or fail closed. Save both agents with `--wait --publish`, then record
agent IDs and published version IDs.

#### 3. Put Guild in the application path

Create `integrations/guild_runner.py` (or the platform's supported webhook/
session adapter confirmed during Phase 0) with:

- `distill(event, watched_receipts)`;
- `critique(protocol)`;
- timeouts, schema validation, and captured agent/session/version IDs.

Wire `Brain.human_done()` to call Distiller and then Critic. Persist the
returned protocol only after both responses validate. Store this provenance
with the protocol:

```json
{
  "guild_distiller_session": "...",
  "guild_critic_session": "...",
  "guild_agent_versions": {"distiller": "...", "critic": "..."},
  "critic_verdict": "APPROVE_ELIGIBLE",
  "critic_findings": []
}
```

Change `Brain.approve()` so the owner cannot arm a protocol unless a validated
Guild critic verdict is `APPROVE_ELIGIBLE`. Guild never performs the final
approval; the human remains the authority.

Use `GUILD_MODE=live|fallback`. In live demo mode, a Guild failure must leave
the protocol pending and display the error. The fallback is only for rehearsal
continuity and must be labeled in logs.

#### 4. Make the integration visible

- Add Guild session IDs/version IDs and the critic verdict to `/state`.
- In the UI, link the pending protocol to its critic session and show findings
  beside the human Approve button.
- Keep the P-001 critic session open during judging. The visible session,
  stored provenance, and approval gate must all refer to the same protocol ID.

If time remains, create a small custom Nous REST integration in Guild so the
agents can fetch protocol context through governed tools. This is a stretch;
the live judgment gate above is already the required deep MVP integration.

### Session 3 handoff

- Files: two Guild projects, fixtures, runtime adapter, schemas, and tests.
- Evidence: published agents/versions, good and rejected sessions, stored
  provenance, and a blocked approval after a REJECT verdict.
- Record: workspace, agent IDs, version IDs, invocation method, timeout/fallback
  behavior, and the one-command live demo invocation.

Do not spend MVP time installing unrelated Hub agents, adding third-party
service tools, or polishing long prompts. Typed outputs, adversarial tests,
provenance, and a real approval gate make Guild essential to Nous.

---

## Final integration rehearsal (both sessions, 20 minutes)

1. Start Nous with `GUILD_MODE=live` and `ROCKETRIDE_MODE=local`.
2. Feed the first invoice and record the watched human actions.
3. Finish watching: confirm a real Guild Distiller session, Critic session,
   approve-eligible verdict, and protocol provenance.
4. Feed the second invoice before approval: Nous must refuse it.
5. Approve P-001: confirm RocketRide, not Python, executes the queued event.
6. Feed a third vendor: confirm autonomous execution, receipts, verification,
   and a RocketRide trace tied to that event.
7. Restart Nous and confirm the protocol, Guild provenance, and receipts remain.
8. Repeat with RocketRide Cloud if the public callback is stable.

The MVP is complete only when one event ID can be followed across the Nous
event, Guild sessions, human approval, RocketRide run, action receipts, and
postcondition verification.

## Current official references

- RocketRide Python SDK: https://docs.rocketride.org/develop/python/
- RocketRide pipeline reference: https://docs.rocketride.org/pipeline-reference/
- RocketRide Cloud: https://docs.rocketride.org/cloud/
- Guild CLI: https://docs.guild.ai/cli/getting-started
- Guild agents and versions: https://docs.guild.ai/platform/agents and
  https://docs.guild.ai/guide/versions
