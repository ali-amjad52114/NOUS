"use agent"

import { guildServiceTool, agent, type Task } from "@guildai/agents-sdk"
import { z } from "zod"

const slack_chat_post_message = guildServiceTool("slack", {
  description: "Post a message to a Slack channel or DM.",
  inputSchema: z.object({
    channel: z.string(),
    text: z.string(),
    thread_ts: z.string().optional(),
  }),
})

const tools = { slack_chat_post_message }

const inputSchema = z.object({
  correlation_id: z.string().min(1),
  commitment_id: z.string().min(1),
  to: z.string().min(1),
  text: z.string().min(1),
  thread_ts: z.string().optional(),
})

const outputSchema = z.object({
  commitment_id: z.string(),
  correlation_id: z.string(),
  status: z.enum(["sent", "failed"]),
  connector: z.literal("slack"),
  operation: z.literal("send_message"),
  external_id: z.string().nullable(),
  provider_status: z.string(),
  executed_at: z.string(),
  error: z.string().nullable(),
})

type Input = z.infer<typeof inputSchema>
type Output = z.infer<typeof outputSchema>

async function run(input: Input, task: Task<typeof tools>): Promise<Output> {
  const { text } = await task.llm.generateText({
    system:
      "You post exactly one Slack message via Guild tools using the trusted fields. Never invent an external_id. If post fails, status=failed and external_id=null. Never create calendar events.",
    prompt: `Post one Slack message from INPUT using slack_chat_post_message.
INPUT.to is the Slack channel id or DM destination. Use text exactly. Optional thread_ts if present.
Return ONLY:
{"commitment_id":"...","correlation_id":"...","status":"sent","connector":"slack","operation":"send_message","external_id":"real-slack-ts-or-null","provider_status":"...","executed_at":"ISO-8601","error":null}

INPUT:\n${JSON.stringify(input)}`,
  })
  const json = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "")
  return outputSchema.parse(JSON.parse(json))
}

export default agent({
  description: "Post one Slack message through Guild OAuth after Nous approval.",
  inputSchema,
  outputSchema,
  tools,
  run,
})
