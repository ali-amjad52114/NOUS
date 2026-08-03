# Guild + RocketRide ownership split

Guild owns Gmail / Slack / Google Calendar OAuth (Credentials in Guild).
RocketRide owns orchestration, LaserData (`tool_laserdata_memory`), and FalkorDB (`graph_falkordb`).

## Pipes

| Pipe | Path |
|------|------|
| Gmail ingest | `pipes/P-INGEST-GMAIL.pipe` |
| Slack ingest | `pipes/P-INGEST-SLACK.pipe` |
| Calendar availability | `pipes/P-INGEST-CALENDAR.pipe` |
| Commitment process | `pipes/P-PROCESS-COMMITMENT.pipe` |
| Approved execute | `pipes/P-EXECUTE-ACTION.pipe` |

## Guild agents to publish

From each folder, `guild agent init` (or replace into an existing project), then `guild agent save --wait --publish`:

- `integrations/guild/nous-gmail-reader`
- `integrations/guild/nous-slack-reader`
- `integrations/guild/nous-calendar-reader`
- `integrations/guild/nous-calendar-writer`
- existing `nous-critic` (used by process pipe)

Connect **Gmail**, **Slack**, and **Google Calendar** under Guild → Credentials before live runs.

## Env vars (RocketRide substitution)

```powershell
$env:ROCKETRIDE_OPENAI_KEY='...'
$env:GUILD_API_KEY_ID='...'
$env:GUILD_API_KEY_SECRET='...'
$env:GUILD_WORKSPACE_OWNER='ali.amjad52114'   # adjust to your Guild owner slug
$env:GUILD_WORKSPACE_NAME='...'
$env:LASER_CONNECTION_STRING='user:password@host:port'
$env:FALKOR_HOST='localhost'                  # or FalkorDB Cloud host when Ready
$env:FALKOR_USERNAME=''
$env:FALKOR_PASSWORD=''
```

## Node sequence (all ingest pipes)

`webhook → agent_rocketride`  
controls: `llm_openai`, `memory_internal`, `tool_guild`, `tool_laserdata_memory`  
→ `response_answers`

Process adds `guardrails` + `graph_falkordb` + Guild `nous-critic`.  
Execute uses Guild `nous-calendar-writer` only after `{commitment_id, approved:true}`.

## Verify (after credentials connected)

```powershell
# In Cursor RocketRide: Validate each .pipe
# Then send a webhook payload, e.g. Gmail:
# {"correlation_id":"corr-1","message_id":"<real-gmail-id>"}
```

Live proof requires: Guild connector OAuth, LaserData connection string, FalkorDB reachable, OpenAI key, Guild trigger API key.
