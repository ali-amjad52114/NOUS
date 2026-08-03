# ali.amjad52114~nous-slack-writer

Post one Slack message through Guild OAuth after Nous approval (`P-SEND-MESSAGE` / `P-FOLLOWUP-NUDGE`).

## Publish

```powershell
cd integrations/guild/nous-slack-writer
guild agent init --name nous-slack-writer --template LLM
# replace agent.ts with this folder's agent.ts if init overwrote it
guild agent save --message "v1" --wait --publish
```

Connect **Slack** under Guild → Credentials before live runs.
