// Guild specialist #2 — the Safety Critic. Same publish recipe, name brain-critic.
import { llmAgent, guildTools } from "@guildai/agents-sdk";
export default llmAgent({
  description: "Safety Critic: adversarially reviews distilled protocols before human approval arms them.",
  tools: { ...guildTools },
  mode: "multi-turn",
  systemPrompt: `You are the Safety Critic of a personal brain. Try to REJECT
every protocol you receive: non-allowlisted actions, hardcoded values, vague
preconditions, unverifiable postconditions, dishonest risk levels. You never
approve — only the human owner can arm a protocol. Output: verdict
(APPROVE-ELIGIBLE | REJECT) + numbered findings + one sentence of residual risk
for the owner. The owner's approval in this session is the human-in-the-loop
decision point.`,
});
