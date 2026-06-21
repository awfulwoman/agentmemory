# AgentMemory Vault Rules

This vault is written and maintained by AI agents. It is not a human knowledge base — it is an operational memory store that allows agents to carry context across sessions and across projects.

## Purpose

- Give agents a persistent picture of ongoing work across all projects
- Surface cross-project patterns grounded in observed facts
- Provide session history that survives context resets

## Structure

- `projects/index.md` — brief summary of every active project; always read at session start
- `projects/<name>/PROJECT.md` — full context for a single project; read when working in that directory
- `sessions/YYYY/MM/YYYY-MM-DD-<project>.md` — clean session notes written after each session
- `global/patterns.md` — cross-project patterns derived from session facts (no speculation)
- `global/entities.md` — shared technologies, people, tools referenced across projects

## Rules

1. Facts only. Never write speculation or inference beyond what is directly observed.
2. No secrets. Never write credentials, tokens, passwords, or sensitive personal data.
3. Contradiction rule. If the vault says X and the live repository says Y, trust the repository. Flag the conflict and update the vault.
4. Repo truth wins. Vault notes about code are summaries — the source of truth is always the codebase.

## Reading order at session start

1. Always read `projects/index.md`
2. If working in a known project directory, read `projects/<name>/PROJECT.md`
3. For mid-session cross-project queries, read `projects/index.md` again or use `notesmd-cli search-content`
