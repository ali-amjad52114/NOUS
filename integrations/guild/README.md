# Nous ↔ Guild MVP hookup

The product boundary is intentionally small:

`watched event/actions → typed Distiller → typed Critic → persisted provenance → human approval gate`

Guild only decides whether a protocol is `APPROVE_ELIGIBLE` or `REJECT`. It
never arms a protocol. Nous validates both outputs again and the owner remains
the final authority.

## Five-minute smoke test of an existing Guild environment

This is read/test-only. Do not repair the environment during the smoke test.

```powershell
guild --version
guild auth status
guild doctor

# Run this from any existing, known-good Guild agent project.
guild agent test --ephemeral
# At the prompt send: ping
```

Pass when the CLI is available, authentication and server checks are green,
`ping` returns a response, and the ephemeral session is visible in Guild. Stop
and hand the exact failing command to the environment owner if any check fails.

## Exact 30-minute MVP hookup

### 0–5 minutes: confirm the existing environment

Run the smoke test above. Record the selected workspace name.

### 5–10 minutes: put the checked-in sources into two Guild projects

Use two already initialized Guild agent projects. Replace only their
`agent.ts` files with:

- `integrations/guild/nous-distiller/agent.ts`
- `integrations/guild/nous-critic/agent.ts`

Do not merge them into one agent: separate sessions and versions are part of
the product evidence.

### 10–18 minutes: test the typed contracts

From the Distiller project run `guild agent test --ephemeral` and submit the
contents represented by `fixtures/valid_invoice.json` as its typed event,
receipts, allowlist, and owner input. Confirm a typed protocol is returned.

From the Critic project run `guild agent test --ephemeral` twice:

1. Submit that exact protocol plus the policy object from `guild_runner.py`;
   expect `APPROVE_ELIGIBLE`.
2. Submit `fixtures/forbidden_action.json` or
   `fixtures/missing_approval.json`; expect `REJECT` or schema failure.

### 18–23 minutes: save the two working versions

```powershell
# In the Distiller project
guild agent save --message "Nous typed distiller MVP" --wait --publish
guild agent get
guild agent versions

# In the Critic project
guild agent save --message "Nous safety critic MVP" --wait --publish
guild agent get
guild agent versions
```

Record both agent IDs and published version IDs.

### 23–27 minutes: connect the existing API triggers

Use one existing/new API trigger per published agent and retain each trigger's
Basic Auth credential. The adapter expects:

```powershell
$env:GUILD_WORKSPACE_OWNER='<owner>'
$env:GUILD_WORKSPACE_NAME='<workspace>'
$env:GUILD_DISTILLER_CREDENTIALS='<key-id>:<key-secret>'
$env:GUILD_CRITIC_CREDENTIALS='<key-id>:<key-secret>'
$env:GUILD_DISTILLER_AGENT_ID='<agent-id>'
$env:GUILD_CRITIC_AGENT_ID='<agent-id>'
$env:GUILD_DISTILLER_VERSION='<version-id>'
$env:GUILD_CRITIC_VERSION='<version-id>'
$env:GUILD_MODE='live'
$env:GUILD_TIMEOUT_SECONDS='45'
```

Session metadata wins when Guild returns IDs; explicit ID variables are a
fallback for provenance only. Never put credentials in source or screenshots.

### 27–30 minutes: run the product path

Start Nous and perform one watch flow through `/events`, `/watch/action`, and
`/watch/done`. Then inspect `/state` before calling `/approve`.

Required `/state` evidence on the pending protocol:

- `guild_mode: live` and `guild_schema_validated: true`
- Distiller and Critic agent IDs, version IDs, and distinct session IDs
- `critic_verdict` and `critic_findings`
- `approved: false` until the owner calls `/approve`

Attempt approval once with a `REJECT` fixture and show that Nous refuses it.
Then use the valid invoice flow, confirm `APPROVE_ELIGIBLE`, and have the owner
approve it.

## Fail-closed behavior

Nous persists no protocol if either Guild call times out, errors, or returns an
invalid schema. The watched event remains available for retry and `/state`
shows the Guild error. A valid `REJECT` is persisted with its findings for
visibility, but `Brain.approve()` refuses to arm it. Fallback mode is labeled
and is only for local rehearsal.

## Acceptance criteria

- The Critic receives the exact validated Distiller protocol.
- Both session IDs, agent IDs, version IDs, verdict, and findings persist.
- Invalid/malformed outputs fail closed without creating a protocol.
- `REJECT` can never be armed; `APPROVE_ELIGIBLE` still requires human action.
- `/state` exposes the pending protocol and Guild error/provenance.
- `python -m unittest discover -s tests -v` passes.
- `python demo.py` ends with `ALL CHECKS PASSED`.
