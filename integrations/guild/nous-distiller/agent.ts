"use agent"

import { agent, noTools, type Task } from "@guildai/agents-sdk"
import { z } from "zod"

const action = z.enum(["forward", "label", "archive", "reply", "book", "send_message"])
const scalar = z.union([z.string(), z.number(), z.boolean(), z.null()])

const inputSchema = z.object({
  source_event: z.object({
    id: z.string().min(1),
    trigger_class: z.string().min(1),
    fields: z.record(z.string(), scalar),
  }),
  watched_receipts: z.array(z.object({
    order: z.number().int().positive(),
    action,
    params: z.record(z.string(), z.unknown()),
  })).min(1),
  allowed_actions: z.array(action).min(1),
  owner_id: z.string().min(1),
})

const protocolSchema = z.object({
  name: z.string().min(1),
  trigger_class: z.string().min(1),
  signature_example: z.string().min(1),
  preconditions: z.array(z.object({
    field: z.string().min(1), operator: z.string().min(1), value: z.unknown(),
  })).min(1),
  steps: z.array(z.object({ action, params: z.record(z.string(), z.unknown()) })).min(1),
  postcondition: z.object({ checks: z.array(z.object({
    kind: z.literal("receipt_exists"), action,
  })).min(1) }),
  risk: z.enum(["low", "medium", "high"]),
})

type Input = z.infer<typeof inputSchema>
type Output = z.infer<typeof protocolSchema>

async function run(input: Input, task: Task<typeof noTools>): Promise<Output> {
  const { text } = await task.llm.generateText({
    system: "Return one JSON object only. Do not use Markdown fences or add wrapper keys.",
    prompt: `You are Nous Distiller. Compile the watched receipts into one reusable protocol.
Return only valid JSON matching the required output schema. Preserve receipt order. Use only allowed_actions. Never invent an
action. Generalize item-specific values into $variables unless the value is a stable owner policy
destination. Include protocol.approved equals true as a typed precondition. Every step must have
a matching receipt_exists postcondition. Do not claim approval; the human owner remains final.
The output trigger_class MUST exactly equal source_event.trigger_class. Derive name and
signature_example from source_event; never copy invoice-specific example values unless the source
event is actually an invoice.

The exact output shape example below demonstrates structure only; its values are not defaults:
{"name":"Handle incoming invoice","trigger_class":"incoming_invoice","signature_example":"invoice message with attachment","preconditions":[{"field":"protocol.approved","operator":"equals","value":true}],"steps":[{"action":"forward","params":{"to":"accounting@myfirm.com"}}],"postcondition":{"checks":[{"kind":"receipt_exists","action":"forward"}]},"risk":"low"}
Do not add a protocol wrapper. Include every watched step and a matching postcondition check.

INPUT:\n${JSON.stringify(input)}`,
  })
  const json = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "")
  return protocolSchema.parse(JSON.parse(json))
}

export default agent({ inputSchema, outputSchema: protocolSchema, tools: noTools, run })
