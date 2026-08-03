"use agent"

import { agent, noTools, type Task } from "@guildai/agents-sdk"
import { z } from "zod"

const action = z.enum(["forward", "label", "archive", "reply", "book", "send_message"])
const protocolSchema = z.object({
  name: z.string().min(1),
  trigger_class: z.string().min(1),
  signature_example: z.string().min(1),
  preconditions: z.array(z.object({
    field: z.string().min(1), operator: z.string().min(1), value: z.unknown(),
  })).min(1),
  steps: z.array(z.object({ action: z.string(), params: z.record(z.string(), z.unknown()) })).min(1),
  postcondition: z.unknown(),
  risk: z.enum(["low", "medium", "high"]),
})
const inputSchema = z.object({
  protocol: protocolSchema,
  policy: z.object({
    allowed_actions: z.array(action),
    human_final_authority: z.literal(true),
    reject_hardcoded_one_off_values: z.literal(true),
    require_approval_precondition: z.literal(true),
    require_verifiable_postcondition: z.literal(true),
  }),
})
const checksSchema = z.object({
  allowlisted_actions: z.boolean(),
  parameterized_inputs: z.boolean(),
  approval_precondition: z.boolean(),
  verifiable_postcondition: z.boolean(),
})
const outputSchema = z.object({
  verdict: z.enum(["APPROVE_ELIGIBLE", "REJECT"]),
  findings: z.array(z.object({
    number: z.number().int().positive(),
    code: z.string().min(1),
    message: z.string().min(1),
    severity: z.enum(["info", "warning", "critical"]),
  })),
  residual_risk: z.string().min(1),
  checks: checksSchema,
})

type Input = z.infer<typeof inputSchema>
type Output = z.infer<typeof outputSchema>

async function run(input: Input, task: Task<typeof noTools>): Promise<Output> {
  const { text } = await task.llm.generateText({
    system: "Return one JSON object only. Do not use Markdown fences or add wrapper keys.",
    prompt: `You are the adversarial Nous Safety Critic. Evaluate all four normalized checks.
REJECT if any action is outside policy, any one-off entity is hardcoded instead of parameterized,
protocol.approved=true is absent as a typed precondition, or every step lacks a receipt_exists
postcondition. Findings must be contiguously numbered. APPROVE_ELIGIBLE only means the protocol
may be shown to its human owner; you never arm or approve it.

An owner's stable policy destination such as accounting@myfirm.com and a stable workflow label
such as invoices are not one-off entity values. A vendor/customer/person identity, invoice number,
amount, date, or source address hardcoded into a reusable protocol is a one-off value and must be
rejected. The findings array contains objects only, never bare numbers or strings.

The exact output shape is:
{"verdict":"APPROVE_ELIGIBLE","findings":[],"residual_risk":"Human owner must still approve execution.","checks":{"allowlisted_actions":true,"parameterized_inputs":true,"approval_precondition":true,"verifiable_postcondition":true}}
A rejection finding has exactly this shape:
{"number":1,"code":"HARDCODED_ONE_OFF","message":"Vendor identity must be parameterized.","severity":"critical"}
Set verdict to REJECT and add numbered finding objects whenever any check is false. Do not add wrapper keys.
Every response, including REJECT, must include verdict, findings, residual_risk, and all four checks.

INPUT:\n${JSON.stringify(input)}`,
  })
  const json = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "")
  return outputSchema.parse(JSON.parse(json))
}

export default agent({ inputSchema, outputSchema, tools: noTools, run })
