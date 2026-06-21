---
name: agent-memory
description: Persistent cross-project memory vault in Obsidian. Loaded proactively at every session to orient the agent.
when: always
---

# Agent Memory

You have access to a persistent memory vault at `~/Documents/Personal/AgentMemory` (or `$AGENT_MEMORY_VAULT`).
This vault stores your memory across sessions and projects. It is written by you, not by the user.

## At session start (proactive)

The SessionStart hook has already injected `projects/index.md` and the current project page into
your context. Read them — they tell you what has been worked on recently across all projects.

If you do not see vault context injected above, read it yourself:

```bash
cat ~/Documents/Personal/AgentMemory/projects/index.md
cat ~/Documents/Personal/AgentMemory/projects/<current-project>/PROJECT.md
```

Where `<current-project>` is the basename of the git root (or current directory if not in a git repo).

## During a session

**Read from the vault when:**
- The user asks what has been worked on recently or across projects
- You need context about a project you haven't seen yet this session
- You want to check for prior decisions before suggesting an approach

**Do not write to the vault during a session.** The hooks handle all writes automatically.

**To search the vault mid-session:**
```bash
grep -r "search term" ~/Documents/Personal/AgentMemory --include="*.md" -l
```

**To read a specific project:**
```bash
cat ~/Documents/Personal/AgentMemory/projects/<name>/PROJECT.md
```

## Rules

1. **Facts only.** Never write speculation. Only record what directly happened or was decided.
2. **No secrets.** Never write credentials, tokens, passwords, or sensitive data to the vault.
3. **Contradiction rule.** If the vault says X and the live codebase says Y, trust the codebase.
    Flag the conflict and note it — the session-end hook will capture it.
4. **Repo truth wins.** Vault notes about code are summaries — the codebase is always the source of truth.

## What belongs here vs native Claude memory

- **Native Claude memory** (`~/.claude/projects/.../memory/`): facts about the *user* — preferences,
  feedback, working conventions specific to how this user likes to work.
- **AgentMemory vault**: facts about the *work* — project state, session history, cross-project patterns.

When deciding where to write something, ask: is this about the user, or about the project?
