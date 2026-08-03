# ali.amjad52114~nous-gmail-writer

Send one Gmail message through Guild OAuth after Nous approval (`P-SEND-MESSAGE` / `P-FOLLOWUP-NUDGE`).

## Publish

```powershell
cd integrations/guild/nous-gmail-writer
guild agent init --name nous-gmail-writer --template LLM
# replace agent.ts with this folder's agent.ts if init overwrote it
guild agent save --message "v1" --wait --publish
```

Connect **Gmail** under Guild → Credentials before live runs.
