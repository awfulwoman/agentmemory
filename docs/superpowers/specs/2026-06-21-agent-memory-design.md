# Agent Memory Wiki — Design Spec

**Date:** 2026-06-21  
**Status:** Approved for implementation  
**Directory:** `~/Documents/AgentMemory` (Obsidian vault)

---

## Problem

Claude Code (and other AI agents) lose context between sessions. The native Claude Code memory system partially addresses this but is per-project, Claude-specific, and not browseable across projects. There is no way for an agent to notice patterns across multiple projects or to carry a longer-running picture of ongoing work.

---

## Goals

- Give agents a persistent, cross-project memory store that survives session boundaries
- Enable an agent starting work in any directory to immediately know what else is being worked on
- Allow any agent (not just Claude Code) to read from and write to the store
- Human-readable and browseable in Obsidian, but written by agents — not by the user
- Foundation for async "dreaming" consolidation (Phase 3)

---

## Approach

**Approach C — Flat hybrid with projects index.** A dedicated Obsidian vault (`AgentMemory`) with three top-level areas: `projects/` (per-project pages), `sessions/` (raw session logs), and `global/` (cross-project patterns and shared entities). A single `projects/index.md` gives every agent a brief overview of all active projects at minimal token cost.

Chosen over:
- Karpathy-style wiki (index-first navigation adds session-start cost without clear benefit at current scale)
- mithunyc tiered capsules (more upfront structure to maintain than needed to start)

---

## Vault Structure

```
~/Documents/AgentMemory/
├── VAULT_RULES.md                        ← universal entrypoint for any agent
├── projects/
│   ├── index.md                          ← always read at session start; 3-5 lines per project
│   ├── llmwiki/
│   │   └── PROJECT.md
│   ├── personal-site/
│   │   └── PROJECT.md
│   ├── infra/
│   │   └── PROJECT.md
│   └── <name>/
│       └── PROJECT.md
├── sessions/
│   └── YYYY/
│       └── MM/
│           ├── YYYY-MM-DD-<project>.md   ← clean session note (after processing)
│           └── YYYY-MM-DD-<project>.wip.md ← raw incremental log (during session)
└── global/
    ├── patterns.md                       ← cross-project patterns (facts only)
    └── entities.md                       ← shared people, tools, technologies
```

Per-project directories (`projects/<name>/`) are designed to grow — context capsules, ADRs, and component notes can be added later without restructuring.

---

## Note Formats

### `projects/index.md`
Loaded at every session start. Kept short — 3-5 lines per project, agent-maintained.

```markdown
## llmwiki
Path: ~/Code/awfulwoman/llmwiki | Status: active
Designing Obsidian-based agent memory system. Last session: 2026-06-21.

## infra
Path: ~/Code/awfulwoman/infra | Status: active
Ansible playbooks for homelab. Last touched: 2026-06-18.
```

### `projects/<name>/PROJECT.md`
Full project context. Read when the agent's working directory matches the project.

```markdown
---
name: llmwiki
path: ~/Code/awfulwoman/llmwiki
status: active
last_session: 2026-06-21
---

## Current focus
Designing the AgentMemory vault spec.

## Key decisions
- Obsidian vault with Obsidian Sync for cross-machine access
- Skills + hooks for Claude Code integration
- Dumb hooks (no Claude tokens during session); one API call at session end

## Known constraints
- notesmd-cli required on each machine
- `AGENT_MEMORY_VAULT` env var must be set (default: `~/Documents/AgentMemory`)
- `ANTHROPIC_API_KEY` must be set for the `SessionEnd` hook's API call
```

### `sessions/YYYY/MM/YYYY-MM-DD-<project>.wip.md`
Written incrementally during the session by dumb hook scripts. Raw facts only.

```markdown
---
project: llmwiki
date: 2026-06-21
agent: claude-code
status: wip
---

[09:14] Session started
[09:15] User asked: how should we structure the vault?
[09:32] Edited docs/superpowers/specs/2026-06-21-agent-memory-design.md
[09:45] git commit: "add agent memory design spec"
[10:02] User asked: how does this interact with native Claude memory?
```

### `sessions/YYYY/MM/YYYY-MM-DD-<project>.md`
Clean session note, written by a single Claude API call at session end from the WIP log.

```markdown
---
project: llmwiki
date: 2026-06-21
agent: claude-code
---

## What was worked on
Designed the AgentMemory vault spec: vault structure, note formats, hook strategy, 
relationship to native Claude memory.

## Decisions made
- Dumb hooks write raw WIP logs; one API call processes them at session end
- Native Claude memory to be replaced in Phase 2 after vault is proven

## Open questions
- notesmd-cli version compatibility across machines
```

### `VAULT_RULES.md`
Plain prose. Explains vault purpose, structure, and rules to any agent reading it. No frontmatter.

---

## Claude Code Integration

### Hooks

All hook scripts are dumb Python scripts. They write raw data to disk — no Claude token cost during the session.

| Hook | Action |
|---|---|
| `SessionStart` | Derive project name from `git rev-parse --show-toplevel` (fallback: `basename $CWD`). Read `projects/index.md` + current `PROJECT.md` via notesmd-cli; inject into context. Create today's `.wip.md`. |
| `Stop` | Append timestamped fact line to `.wip.md` (files edited, git commits, prompt topic). |
| `PreCompact` | Flush WIP buffer to disk before context compression. |
| `SessionEnd` | Call Python script → one Claude API call → process `.wip.md` → write clean session note + update `PROJECT.md` + update `projects/index.md`. Rename `.wip.md` → `.md`. |

**Hook scripts location:** `~/.claude/hooks/agent-memory/`

If `SessionEnd` never fires (killed session), the `.wip.md` remains and is processed by the dreaming cron job in Phase 3.

### Skill

`~/.claude/skills/agent-memory/SKILL.md` teaches Claude:

- What the vault is and where it lives (`$AGENT_MEMORY_VAULT` or `~/Documents/AgentMemory`)
- What each folder contains
- Facts only: no secrets, no speculation
- Contradiction rule: if vault says X but the repo says Y, trust the repo, flag the conflict, update the vault
- When to read mid-session: if the user asks cross-project questions or "what have I been working on?", read `projects/index.md` via notesmd-cli
- What to write and what to leave alone

### Data Flow

```
SESSION START
  SessionStart hook (Python)
    → obsidian CLI reads projects/index.md
    → obsidian CLI reads projects/<name>/PROJECT.md (if exists)
    → injects both into Claude context
    → creates sessions/YYYY/MM/YYYY-MM-DD-<project>.wip.md

DURING SESSION
  Stop hook (Python) after each response
    → appends timestamped facts to .wip.md
    → no LLM involvement, no token cost

  PreCompact hook (Python) before context compression
    → flushes WIP buffer to disk

SESSION END (clean)
  SessionEnd hook (Python → Claude API)
    → reads .wip.md
    → writes clean sessions/YYYY/MM/YYYY-MM-DD-<project>.md
    → updates projects/<name>/PROJECT.md
    → updates projects/index.md
    → deletes .wip.md

SESSION END (interrupted)
  .wip.md left on disk
  Phase 3 dreaming cron processes it

MID-SESSION QUERIES
  Skill instructs Claude to read projects/index.md or search vault via notesmd-cli
```

### notesmd-cli Command Reference

Vault must be registered once per machine:
```bash
notesmd-cli add-vault ~/Documents/AgentMemory --set-default
```

Commands used by hook scripts:

```bash
# Read a note (session start)
notesmd-cli print "projects/index.md" --vault "AgentMemory"
notesmd-cli print "projects/llmwiki/PROJECT.md" --vault "AgentMemory"

# Create session WIP file
notesmd-cli create "sessions/2026/06/2026-06-21-llmwiki.wip.md" \
  --content "..." --vault "AgentMemory"

# Append to WIP file (Stop hook)
notesmd-cli create "sessions/2026/06/2026-06-21-llmwiki.wip.md" \
  --content "[14:32] Edited src/memory.py" --append --vault "AgentMemory"

# Overwrite project page (SessionEnd)
notesmd-cli create "projects/llmwiki/PROJECT.md" \
  --content "..." --overwrite --vault "AgentMemory"

# Update frontmatter field
notesmd-cli frontmatter "projects/llmwiki/PROJECT.md" \
  --edit --key "last_session" --value "2026-06-21" --vault "AgentMemory"

# Rename .wip.md → .md on clean session end
notesmd-cli move "sessions/2026/06/2026-06-21-llmwiki.wip.md" \
  "sessions/2026/06/2026-06-21-llmwiki.md" --vault "AgentMemory"

# Search vault mid-session
notesmd-cli search-content "auth middleware" --format json --vault "AgentMemory"
```

### Implementation Files

```
~/.claude/
  skills/agent-memory/SKILL.md
  hooks/agent-memory/session-start.py
  hooks/agent-memory/stop.py
  hooks/agent-memory/pre-compact.py
  hooks/agent-memory/session-end.py
```

---

## Relationship to Native Claude Memory

The native Claude Code memory system (`~/.claude/projects/<path-hash>/memory/`) is **not replaced in Phase 1**. The two systems coexist with clear content boundaries:

| | Native Claude memory | AgentMemory vault |
|---|---|---|
| Content | User preferences, feedback, working conventions | Project state, session logs, cross-project patterns |
| Scope | Per-project, Claude Code only | Cross-project, multi-agent |
| Written by | Claude Code only | Any agent |

The skill explicitly tells Claude which system to use for which type of information.

---

## Phases

### Phase 1 — Core vault (this spec)
- Vault structure + note formats
- Claude Code skill
- Hook scripts (SessionStart, Stop, PreCompact, SessionEnd)
- `VAULT_RULES.md`
- Manual testing: a few projects, verify session logs are written and PROJECT.md stays current

### Phase 2 — Native memory migration
- Python migration script: reads all `~/.claude/projects/*/memory/` directories, uses Claude API to consolidate each into a `projects/<name>/PROJECT.md` in AgentMemory
- Migrate global native memories → `global/user-prefs.md`, `global/feedback.md`
- Update skill to stop writing to native memory
- Leave native memory empty (or a single pointer note)

### Phase 3 — Dreaming (stretch goal)
- Python script on `malcolm`, cron in early hours
- Reads recent session logs + any leftover `.wip.md` files
- Makes Claude API calls to:
  - Process orphaned `.wip.md` files into clean session notes
  - Update `projects/index.md` with fresh one-line summaries
  - Update `global/patterns.md` with cross-project patterns grounded in session facts (no speculation)
- Obsidian Sync propagates results to all machines

---

## Key Design Decisions

- **Obsidian Sync** for cross-machine availability — no shared network path, no infra to manage
- **`notesmd-cli`** ([yakitrak/notesmd-cli](https://github.com/Yakitrak/notesmd-cli)) for all vault reads/writes — works without Obsidian running, suitable for hooks and headless cron on `malcolm`
- **Dumb hooks** — zero Claude token cost during sessions; one API call per session end
- **`.wip.md` pattern** — resilient to interruption; dreaming processes orphans
- **`projects/index.md`** — the key cross-project primitive; brief, always loaded, agent-maintained
- **Facts only** — no speculation in any agent-written note; contradiction rule enforces repo as source of truth
- **Per-project directories** — `projects/<name>/` designed to grow without restructuring
