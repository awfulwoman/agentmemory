# agentmemory

Persistent cross-project memory for Claude Code sessions. Hooks capture what was worked on during a session; a Claude Haiku call at session end summarises it into a markdown vault that gets injected at the start of every future session.

## How it works

Four Claude Code hooks write to a local vault at `~/Documents/Personal/AgentMemory`:

| Hook | Trigger | What it does |
|------|---------|--------------|
| `session_start.py` | Session open | Injects `projects/index.md` and the current project page into context |
| `post_tool_use.py` | Edit / Write | Appends a timestamped line to the session WIP log |
| `pre_compact.py` | Before compaction | Appends a checkpoint marker to the WIP log |
| `session_end.py` | Session close | Sends the WIP log to `claude haiku`, writes a session note and updates the project page |

A skill (`src/skills/agent-memory/SKILL.md`) is installed into `~/.claude/skills/` so Claude knows how to read from the vault mid-session.

## Vault structure

```
~/Documents/Personal/AgentMemory/
  projects/
    index.md                        # one-liner per active project; always loaded at session start
    <name>/PROJECT.md               # full context for a project; loaded when working in that directory
  sessions/YYYY/MM/
    YYYY-MM-DD-<project>.wip.md     # live log, deleted after session_end processes it
    YYYY-MM-DD-<project>.md         # clean session note written by haiku
  global/
    patterns.md                     # cross-project patterns
    entities.md                     # shared tools, people, technologies
```

## Install

Requires Python 3 and the `claude` CLI on `$PATH`.

```bash
python3 install.py
```

This copies hooks and skill into `~/.claude/`, wires the hooks into `~/.claude/settings.json`, bootstraps the vault skeleton, and adds the files to chezmoi.

Start a new Claude Code session to activate.

## Configuration

Set `$AGENT_MEMORY_VAULT` to override the default vault location.
