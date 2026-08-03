"use agent"

import { gmailTools } from "@guildai-services/guildai~gmail"
import { agent, pick, type Task } from "@guildai/agents-sdk"
import { z } from "zod"

const tools = {
  ...pick(gmailTools, ["gmail_messages_send"]),
}

const inputSchema = z.object({
  correlation_id: z.string().min(1),
  commitment_id: z.string().min(1),
  to: z.string().min(1),
  text: z.string().min(1),
  subject: z.string().optional(),
})

const outputSchema = z.object({
  commitment_id: z.string(),
  correlation_id: z.string(),
  status: z.enum(["sent", "failed"]),
  connector: z.literal("gmail"),
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
      "You send exactly one Gmail message via Guild tools using the trusted fields. Never invent an external_id. If send fails, status=failed and external_id=null. Never create calendar events.",
    prompt: `Send one Gmail message from INPUT using gmail_messages_send.
Use to/text/subject exactly (subject may default to a short commitment follow-up).
Return ONLY:
{"commitment_id":"...","correlation_id":"...","status":"sent","connector":"gmail","operation":"send_message","external_id":"real-gmail-id-or-null","provider_status":"...","executed_at":"ISO-8601","error":null}

INPUT:\n${JSON.stringify(input)}`,
  })
  const json = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "")
  return outputSchema.parse(JSON.parse(json))
}

export default agent({
  description: "Send one Gmail message through Guild OAuth after Nous approval.",
  inputSchema,
  outputSchema,
  tools,
  run,
})
