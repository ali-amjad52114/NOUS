# Guild Session 3 evidence

Date: 2026-08-03
Workspace: `win-hackathon` (`019eba36-d65d-3bb9-0000-95bb488524b5`)
Authenticated user: `ali.amjad52114`

## Phase 0

- Nous baseline: `ALL CHECKS PASSED`
- Smoke agent: `nous-phase0-smoke` (`019fc918-6ef1-726e-0000-af790bdff3a6`)
- Ephemeral pong session: `019fc91a-c684-f268-0000-6426cfa3ab48`
- Validated draft version: `019fc91b-3ba5-cf83-0000-e245725b4366`

## Published agents

- Distiller agent: `nous-distiller` (`019fc91c-9123-726e-0000-2190722ef99a`)
- Distiller published version: `019fc926-f0e7-cf83-0000-13e6ced1ee49`
- Typed valid-invoice session: `019fc926-5188-f268-0000-fd6320d5f5a8`
- Critic agent: `nous-critic` (`019fc928-4597-726e-0000-d738cae54340`)
- Critic published version: `019fc933-e35b-cf83-0000-e199ea8f2d56`
- Approve-eligible session: `019fc92c-e17a-f268-0000-9b153622015b`
- Rejected unsafe session: `019fc930-0548-f268-0000-53cecf6e3eaa`

The unsafe session rejected a non-allowlisted `delete` action, a hardcoded vendor identity,
and a missing verifiable postcondition. The valid session returned `APPROVE_ELIGIBLE` while
retaining the human owner as the final approval authority.

Final verification: 11 Guild integration tests passed and `demo.py` printed
`ALL CHECKS PASSED — demo is stage-ready`.
