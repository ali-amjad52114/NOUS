---
name: guild-agent-dev
description: Use when working on Guild agents with Codex: creating agents, editing agent code, testing with the Guild CLI, saving versions, publishing, debugging sessions, or answering questions about Guild agent development.
---

# Guild Agent Development

Use the Guild CLI for local agent development. Prefer commands that are scriptable and safe for a coding agent to run.

## First Checks

Before changing an agent, establish the local context:

```bash
guild --version
guild auth status
guild workspace current
```

If authentication or workspace selection is missing, tell the user the exact command to run:

```bash
guild auth login
guild workspace select
```

## Core Rules

- Use `guild agent init`, `guild agent clone`, `guild agent pull`, `guild agent test`, `guild agent chat`, and `guild agent save` for agent lifecycle work.
- Do not edit `guild.json`; it is managed by the CLI.
- Prefer `guild agent save -A --message "..."` instead of raw `git commit` or `git push`. Note `-A` commits modified tracked files only; run `git add <file>` first to include new files.
- Do not use `git push` directly for agent repositories; use `guild agent save`.
- Keep edits scoped to the agent files requested by the user.
- Surface command output that matters, especially validation errors, session links, workspace IDs, and next commands.

## Common Workflows

Create a new agent:

```bash
mkdir my-agent && cd my-agent
guild agent init --name my-agent --template LLM
```

Clone an existing agent:

```bash
guild agent clone owner~agent-name
cd agent-name
```

Sync before editing when collaborating:

```bash
guild agent pull
```

Test unsaved local changes:

```bash
guild agent test --ephemeral
```

For non-interactive Codex test loops, prefer JSON input:

```bash
printf '{"type":"text","text":"hello"}\n' | guild agent test --ephemeral --mode json
```

Send a single message to the agent in the current directory:

```bash
guild agent chat --ephemeral "Hello"
```

Save a draft version (`-A` commits modified tracked files only; `git add` new files first):

```bash
guild agent save -A --message "Describe the change"
```

Save, validate, and publish:

```bash
guild agent save -A --message "Ready" --wait --publish
```

## Debugging

If a test fails or stalls:

```bash
guild doctor
guild agent versions
guild session events <session-id>
guild session tasks <session-id>
```

Use `--events all` to see system events (runtime lifecycle, agent console, LLM start/done):

```bash
guild agent test --ephemeral --events all
```

## Agent Code Patterns

LLM agents use a prompt and tools:

```typescript
import { llmAgent, guildTools } from '@guildai/agents-sdk';

export default llmAgent({
  description: 'Helps users with Guild workspaces',
  tools: { ...guildTools },
  systemPrompt: `You are a helpful Guild workspace assistant.`,
  mode: 'multi-turn',
});
```

To let an LLM agent use account skills, import `skillsTools` from the SDK. Skills are account-scoped Markdown instructions; they are not one npm package per skill.

```typescript
import { llmAgent, skillsTools, userInterfaceTools } from '@guildai/agents-sdk';

export default llmAgent({
  description: 'Uses account skills when they are relevant',
  tools: {
    ...skillsTools,
    ...userInterfaceTools,
  },
  systemPrompt: `
    When account-specific knowledge would help, inspect the skill catalog and
    activate the relevant skill before applying its instructions.
  `,
});
```

Do not add dependencies such as `@guildai-services/acme~brand-voice` for individual skills. If the behavior needs API access, code execution, credentials, or a separate tool set, build an integration or agent instead.

Code-first agents call tools through `task.tools`:

```typescript
'use agent';

import { agent, guildTools, type Task } from '@guildai/agents-sdk';
import { z } from 'zod';

const tools = { ...guildTools };
type Tools = typeof tools;

const inputSchema = z.object({
  type: z.literal('text'),
  text: z.string(),
});

const outputSchema = z.object({
  type: z.literal('text'),
  text: z.string(),
});

async function run(input: z.infer<typeof inputSchema>, task: Task<Tools>) {
  await task.tools.guild_debug_log({ message: input.text });
  return { type: 'text' as const, text: input.text };
}

export default agent({
  description: 'Echoes user text',
  inputSchema,
  outputSchema,
  tools,
  run,
});
```

All tool calls go through `task.tools.<toolName>(args)`.
