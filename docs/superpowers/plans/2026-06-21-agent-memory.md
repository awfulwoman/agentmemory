# Agent Memory Wiki — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent cross-project agent memory vault in Obsidian, wired into Claude Code via skills and hooks, with dumb hook scripts that write raw session logs and one Claude API call at session end to produce clean notes.

**Architecture:** A dedicated Obsidian vault (`~/Documents/AgentMemory`) stores per-project pages, dated session logs, and global cross-project patterns. Four Python hook scripts (SessionStart, PostToolUse, PreCompact, SessionEnd) run automatically in Claude Code. A skill tells Claude what the vault is and how to use it mid-session. `notesmd-cli` is the sole interface to the vault filesystem — no raw file I/O.

**Tech Stack:** Python 3.14, `notesmd-cli` (brew), `anthropic` Python SDK, Claude Code hooks (settings.json), Claude Code skills (SKILL.md), Obsidian + Obsidian Sync.

## Global Constraints

- All vault access via `notesmd-cli` — never raw `open()`/`pathlib` on vault files
- Hook scripts write zero Claude tokens during session; only `session-end.py` calls the Claude API
- Model for session-end API call: `claude-haiku-4-5-20251001` (fast, cheap)
- Vault name: `AgentMemory`; default path: `~/Documents/AgentMemory`; override via `AGENT_MEMORY_VAULT` env var
- Project name derived from: `git rev-parse --show-toplevel` → `basename`; fallback `basename($CWD)`
- Facts only in all vault writes — no speculation, no secrets
- All Python scripts must pass `pytest` before being deployed
- Skill and hooks added to chezmoi after deployment

---

## File Map

```
~/Code/awfulwoman/llmwiki/        ← this repo (development home)
  src/
    hooks/
      common.py                   ← shared utilities (vault path, project name, notesmd-cli wrapper)
      session-start.py            ← SessionStart hook
      post-tool-use.py            ← PostToolUse hook (Edit/Write filter)
      pre-compact.py              ← PreCompact hook
      session-end.py              ← SessionEnd hook (calls Claude API)
    vault/                        ← vault template files (bootstrapped into ~/Documents/AgentMemory)
      VAULT_RULES.md
      projects/index.md
      global/patterns.md
      global/entities.md
    skills/
      agent-memory/
        SKILL.md
  tests/
    test_common.py
    test_session_start.py
    test_post_tool_use.py
    test_pre_compact.py
    test_session_end.py
  requirements.txt
  install.py                      ← installs notesmd-cli, bootstraps vault, deploys hooks+skill, wires settings.json

~/.claude/                        ← deployed targets (managed by chezmoi)
  hooks/
    agent-memory/
      common.py
      session-start.py
      post-tool-use.py
      pre-compact.py
      session-end.py
  skills/
    agent-memory/
      SKILL.md
  settings.json                   ← modified to add hooks

~/Documents/AgentMemory/          ← the vault (created by install.py)
  VAULT_RULES.md
  projects/index.md
  global/patterns.md
  global/entities.md
```

---

## Task 1: Dependencies and vault template files

**Files:**
- Create: `requirements.txt`
- Create: `src/vault/VAULT_RULES.md`
- Create: `src/vault/projects/index.md`
- Create: `src/vault/global/patterns.md`
- Create: `src/vault/global/entities.md`

**Interfaces:**
- Produces: vault template content consumed by Task 8 (install.py)

- [ ] **Step 1: Install notesmd-cli**

```bash
brew tap yakitrak/yakitrak
brew install yakitrak/yakitrak/notesmd-cli
notesmd-cli --version
```

Expected: version string printed with no error.

- [ ] **Step 2: Create requirements.txt**

```
anthropic>=0.40.0
pytest>=8.0.0
```

- [ ] **Step 3: Install Python dependencies**

```bash
pip3 install -r requirements.txt
python3 -c "import anthropic; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Create src/vault/VAULT_RULES.md**

```markdown
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
```

- [ ] **Step 5: Create src/vault/projects/index.md**

```markdown
# Projects Index

_Agent-maintained. Updated at each session end._

<!-- Add project entries here as sessions are run. Format:
## <project-name>
Path: ~/Code/... | Status: active|paused|complete
<one sentence current focus>. Last session: YYYY-MM-DD.
-->
```

- [ ] **Step 6: Create src/vault/global/patterns.md**

```markdown
# Cross-Project Patterns

_Agent-maintained. Updated by dreaming process (Phase 3) or manually noted during sessions._

<!-- Format:
## <pattern name>
Observed in: project-a, project-b
<description of the pattern, grounded in facts from session logs>
-->
```

- [ ] **Step 7: Create src/vault/global/entities.md**

```markdown
# Shared Entities

_Agent-maintained. Technologies, people, and tools referenced across multiple projects._

<!-- Format:
## <entity name>
Type: technology|person|tool|service
Used in: project-a, project-b
<one-line description>
-->
```

- [ ] **Step 8: Commit**

```bash
git add requirements.txt src/vault/
git commit -m "feat: vault template files and dependencies"
```

---

## Task 2: common.py — shared hook utilities

**Files:**
- Create: `src/hooks/common.py`
- Create: `tests/test_common.py`

**Interfaces:**
- Produces:
  - `get_vault_path() -> str` — returns absolute vault path
  - `get_project_name(cwd: str) -> str` — returns project name from git root or basename
  - `run_notesmd(args: list[str]) -> str` — runs notesmd-cli, returns stdout
  - `wip_path(project: str, date: str) -> str` — returns vault-relative WIP note path
  - `session_path(project: str, date: str) -> str` — returns vault-relative clean note path

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_common.py
import os
import subprocess
from unittest.mock import patch, MagicMock
import pytest
import sys
sys.path.insert(0, 'src/hooks')
import common


def test_get_vault_path_from_env(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        assert common.get_vault_path() == str(tmp_path)


def test_get_vault_path_default():
    with patch.dict(os.environ, {}, clear=True):
        result = common.get_vault_path()
        assert result == os.path.expanduser('~/Documents/AgentMemory')


def test_get_project_name_from_git(tmp_path):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='/Users/charlie/Code/awfulwoman/myproject\n'
        )
        result = common.get_project_name(str(tmp_path))
        assert result == 'myproject'


def test_get_project_name_fallback_basename(tmp_path):
    project_dir = tmp_path / 'my-project'
    project_dir.mkdir()
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        result = common.get_project_name(str(project_dir))
        assert result == 'my-project'


def test_run_notesmd_returns_stdout():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='note content\n')
        result = common.run_notesmd(['print', 'projects/index.md'])
        assert result == 'note content\n'
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'notesmd-cli'
        assert 'print' in args
        assert 'projects/index.md' in args


def test_run_notesmd_includes_vault_flag():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='')
        with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': '/fake/vault'}):
            common.run_notesmd(['list'])
        args = mock_run.call_args[0][0]
        assert '--vault' in args
        assert 'AgentMemory' in args


def test_wip_path():
    path = common.wip_path('myproject', '2026-06-21')
    assert path == 'sessions/2026/06/2026-06-21-myproject.wip.md'


def test_session_path():
    path = common.session_path('myproject', '2026-06-21')
    assert path == 'sessions/2026/06/2026-06-21-myproject.md'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/charlie/Code/awfulwoman/llmwiki
python3 -m pytest tests/test_common.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `common` not yet defined.

- [ ] **Step 3: Write src/hooks/common.py**

```python
import os
import subprocess
from datetime import date


def get_vault_path() -> str:
    return os.environ.get('AGENT_MEMORY_VAULT', os.path.expanduser('~/Documents/AgentMemory'))


def get_vault_name() -> str:
    return os.path.basename(get_vault_path())


def get_project_name(cwd: str) -> str:
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=2,
    )
    if result.returncode == 0 and result.stdout.strip():
        return os.path.basename(result.stdout.strip())
    return os.path.basename(cwd.rstrip('/'))


def run_notesmd(args: list[str]) -> str:
    cmd = ['notesmd-cli'] + args + ['--vault', get_vault_name()]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result.stdout


def wip_path(project: str, session_date: str) -> str:
    year, month, _ = session_date.split('-')
    return f'sessions/{year}/{month}/{session_date}-{project}.wip.md'


def session_path(project: str, session_date: str) -> str:
    year, month, _ = session_date.split('-')
    return f'sessions/{year}/{month}/{session_date}-{project}.md'


def today() -> str:
    return date.today().isoformat()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_common.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/common.py tests/test_common.py
git commit -m "feat: common hook utilities"
```

---

## Task 3: session-start.py — read vault context, create WIP file

**Files:**
- Create: `src/hooks/session-start.py`
- Create: `tests/test_session_start.py`

**Interfaces:**
- Consumes: `common.get_vault_path`, `common.get_project_name`, `common.run_notesmd`, `common.wip_path`, `common.today`
- Produces: stdout text (vault context injected into Claude session); creates WIP note in vault

Claude Code hook input (stdin):
```json
{"session_id": "abc", "cwd": "/path/to/project"}
```

Claude Code reads this hook's stdout and injects it into the session context.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_session_start.py
import json
import sys
import io
from unittest.mock import patch, MagicMock
import pytest
sys.path.insert(0, 'src/hooks')


def run_hook(stdin_data: dict) -> str:
    stdin_json = json.dumps(stdin_data)
    with patch('sys.stdin', io.StringIO(stdin_json)):
        captured = io.StringIO()
        with patch('sys.stdout', captured):
            import session_start
            import importlib
            importlib.reload(session_start)
            session_start.main()
        return captured.getvalue()


def test_session_start_reads_index(tmp_path):
    calls = []
    def mock_notesmd(args):
        calls.append(args)
        if 'projects/index.md' in args:
            return '## myproject\nPath: ~/Code/myproject | Status: active\n'
        return ''

    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'), \
         patch('common.get_vault_path', return_value=str(tmp_path)):
        import session_start, importlib
        importlib.reload(session_start)
        stdin = json.dumps({'session_id': 'x', 'cwd': '/fake/myproject'})
        with patch('sys.stdin', __import__('io').StringIO(stdin)):
            output = __import__('io').StringIO()
            with patch('sys.stdout', output):
                session_start.main()
        result = output.getvalue()

    assert 'myproject' in result
    assert any('projects/index.md' in str(c) for c in calls)


def test_session_start_creates_wip_file():
    notesmd_calls = []
    def mock_notesmd(args):
        notesmd_calls.append(args)
        return 'content'

    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'), \
         patch('common.get_vault_path', return_value='/fake/vault'):
        import session_start, importlib, io
        importlib.reload(session_start)
        stdin = json.dumps({'session_id': 'abc', 'cwd': '/fake/myproject'})
        with patch('sys.stdin', io.StringIO(stdin)):
            with patch('sys.stdout', io.StringIO()):
                session_start.main()

    create_call = next(
        (c for c in notesmd_calls if 'create' in c and 'wip.md' in str(c)),
        None
    )
    assert create_call is not None, f"No create wip call found in: {notesmd_calls}"
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/test_session_start.py -v
```

Expected: `ModuleNotFoundError: No module named 'session_start'`

- [ ] **Step 3: Write src/hooks/session-start.py**

```python
#!/usr/bin/env python3
import json
import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
import common


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    cwd = data.get('cwd', __import__('os').getcwd())
    project = common.get_project_name(cwd)
    today = common.today()

    index_content = common.run_notesmd(['print', 'projects/index.md'])
    project_content = common.run_notesmd(['print', f'projects/{project}/PROJECT.md'])

    wip = common.wip_path(project, today)
    wip_header = f'---\nproject: {project}\ndate: {today}\nagent: claude-code\nstatus: wip\n---\n\n'
    wip_header += f'[{__import__("datetime").datetime.now().strftime("%H:%M")}] Session started\n'
    common.run_notesmd(['create', wip, '--content', wip_header])

    output = []
    if index_content.strip():
        output.append('## Agent Memory: All Projects\n\n' + index_content.strip())
    if project_content.strip():
        output.append(f'## Agent Memory: {project}\n\n' + project_content.strip())

    if output:
        print('\n\n'.join(output))


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_session_start.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/session-start.py tests/test_session_start.py
git commit -m "feat: session-start hook"
```

---

## Task 4: post-tool-use.py — append file edits to WIP log

**Files:**
- Create: `src/hooks/post-tool-use.py`
- Create: `tests/test_post_tool_use.py`

**Interfaces:**
- Consumes: `common.get_project_name`, `common.run_notesmd`, `common.wip_path`, `common.today`
- Produces: appends one line to the session WIP note

Claude Code hook input (stdin) for PostToolUse:
```json
{
  "session_id": "abc",
  "tool_name": "Edit",
  "tool_input": {"file_path": "/path/to/file.py"},
  "cwd": "/path/to/project"
}
```

Only fires for tool names `Edit` and `Write` (configured in settings.json matcher).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_post_tool_use.py
import json
import sys
import io
from unittest.mock import patch
import pytest
sys.path.insert(0, 'src/hooks')


def run_hook(stdin_data: dict) -> list:
    notesmd_calls = []
    def mock_notesmd(args):
        notesmd_calls.append(args)
        return ''

    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'):
        import post_tool_use, importlib
        importlib.reload(post_tool_use)
        with patch('sys.stdin', io.StringIO(json.dumps(stdin_data))):
            with patch('sys.stdout', io.StringIO()):
                post_tool_use.main()
    return notesmd_calls


def test_edit_tool_appends_to_wip():
    calls = run_hook({
        'session_id': 'x',
        'tool_name': 'Edit',
        'tool_input': {'file_path': '/Users/charlie/Code/myproject/src/foo.py'},
        'cwd': '/Users/charlie/Code/myproject',
    })
    append_call = next((c for c in calls if '--append' in c), None)
    assert append_call is not None
    content = append_call[append_call.index('--content') + 1]
    assert 'foo.py' in content
    assert 'edit' in content.lower()


def test_write_tool_appends_to_wip():
    calls = run_hook({
        'session_id': 'x',
        'tool_name': 'Write',
        'tool_input': {'file_path': '/Users/charlie/Code/myproject/new_file.py'},
        'cwd': '/Users/charlie/Code/myproject',
    })
    assert any('--append' in c for c in calls)


def test_read_tool_ignored():
    calls = run_hook({
        'session_id': 'x',
        'tool_name': 'Read',
        'tool_input': {'file_path': '/some/file.py'},
        'cwd': '/Users/charlie/Code/myproject',
    })
    assert not any('--append' in c for c in calls)


def test_wip_path_used():
    calls = run_hook({
        'session_id': 'x',
        'tool_name': 'Edit',
        'tool_input': {'file_path': '/Users/charlie/Code/myproject/src/foo.py'},
        'cwd': '/Users/charlie/Code/myproject',
    })
    append_call = next((c for c in calls if '--append' in c), None)
    assert 'sessions/2026/06/2026-06-21-myproject.wip.md' in str(append_call)
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/test_post_tool_use.py -v
```

Expected: `ModuleNotFoundError: No module named 'post_tool_use'`

- [ ] **Step 3: Write src/hooks/post-tool-use.py**

```python
#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
import common

TRACKED_TOOLS = {'edit', 'write'}


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    tool_name = data.get('tool_name', '')
    if tool_name.lower() not in TRACKED_TOOLS:
        return

    cwd = data.get('cwd', os.getcwd())
    project = common.get_project_name(cwd)
    today = common.today()
    wip = common.wip_path(project, today)

    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', tool_input.get('path', ''))
    short_path = os.path.relpath(file_path, cwd) if file_path and cwd else file_path

    timestamp = datetime.now().strftime('%H:%M')
    line = f'[{timestamp}] {tool_name.lower()}: {short_path}\n'

    common.run_notesmd(['create', wip, '--content', line, '--append'])


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_post_tool_use.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/post-tool-use.py tests/test_post_tool_use.py
git commit -m "feat: post-tool-use hook"
```

---

## Task 5: pre-compact.py — checkpoint before context compression

**Files:**
- Create: `src/hooks/pre-compact.py`
- Create: `tests/test_pre_compact.py`

**Interfaces:**
- Consumes: `common.get_project_name`, `common.run_notesmd`, `common.wip_path`, `common.today`
- Produces: appends one checkpoint line to WIP note

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pre_compact.py
import json
import sys
import io
from unittest.mock import patch
import pytest
sys.path.insert(0, 'src/hooks')


def run_hook(cwd='/fake/myproject'):
    notesmd_calls = []
    def mock_notesmd(args):
        notesmd_calls.append(args)
        return ''

    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'):
        import pre_compact, importlib
        importlib.reload(pre_compact)
        stdin = json.dumps({'session_id': 'x', 'cwd': cwd})
        with patch('sys.stdin', io.StringIO(stdin)):
            with patch('sys.stdout', io.StringIO()):
                pre_compact.main()
    return notesmd_calls


def test_pre_compact_appends_checkpoint():
    calls = run_hook()
    append_call = next((c for c in calls if '--append' in c), None)
    assert append_call is not None
    content = append_call[append_call.index('--content') + 1]
    assert 'compact' in content.lower() or 'checkpoint' in content.lower()


def test_pre_compact_targets_wip_file():
    calls = run_hook()
    append_call = next((c for c in calls if '--append' in c), None)
    assert 'sessions/2026/06/2026-06-21-myproject.wip.md' in str(append_call)
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/test_pre_compact.py -v
```

Expected: `ModuleNotFoundError: No module named 'pre_compact'`

- [ ] **Step 3: Write src/hooks/pre-compact.py**

```python
#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
import common


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    cwd = data.get('cwd', os.getcwd())
    project = common.get_project_name(cwd)
    today = common.today()
    wip = common.wip_path(project, today)

    timestamp = datetime.now().strftime('%H:%M')
    line = f'[{timestamp}] ---pre-compact checkpoint---\n'
    common.run_notesmd(['create', wip, '--content', line, '--append'])


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_pre_compact.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/pre-compact.py tests/test_pre_compact.py
git commit -m "feat: pre-compact hook"
```

---

## Task 6: session-end.py — process WIP into clean session note

**Files:**
- Create: `src/hooks/session-end.py`
- Create: `tests/test_session_end.py`

**Interfaces:**
- Consumes: `common.*`, `anthropic` SDK, `ANTHROPIC_API_KEY` env var
- Produces: clean session note at `sessions/YYYY/MM/YYYY-MM-DD-<project>.md`, updated `projects/<name>/PROJECT.md`, updated entry in `projects/index.md`; deletes WIP file

The Claude API call uses a structured prompt that returns JSON:
```json
{
  "session_note": "## What was worked on\n...\n\n## Decisions made\n...\n\n## Open questions\n...",
  "current_focus": "one sentence",
  "decisions": ["decision 1", "decision 2"],
  "index_line": "one sentence status update. Last session: YYYY-MM-DD."
}
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_session_end.py
import json
import sys
import io
import os
from unittest.mock import patch, MagicMock
import pytest
sys.path.insert(0, 'src/hooks')

SAMPLE_WIP = """---
project: myproject
date: 2026-06-21
agent: claude-code
status: wip
---

[09:14] Session started
[09:32] edit: src/memory.py
[09:45] edit: tests/test_memory.py
[09:50] ---pre-compact checkpoint---
"""

SAMPLE_CLAUDE_RESPONSE = json.dumps({
    "session_note": "## What was worked on\nEdited memory.py and tests.\n\n## Decisions made\nUsed append mode.\n\n## Open questions\nNone.",
    "current_focus": "Implementing session-end hook.",
    "decisions": ["Used append mode for WIP files"],
    "index_line": "Implementing agent memory hooks. Last session: 2026-06-21."
})


def make_mock_anthropic(response_text):
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_client.messages.create.return_value = mock_message
    return mock_client


def run_hook(wip_content=SAMPLE_WIP, project_content='', index_content=''):
    notesmd_calls = []
    def mock_notesmd(args):
        notesmd_calls.append(list(args))
        if 'print' in args and 'wip.md' in str(args):
            return wip_content
        if 'print' in args and 'PROJECT.md' in str(args):
            return project_content
        if 'print' in args and 'index.md' in str(args):
            return index_content
        return ''

    mock_client = make_mock_anthropic(SAMPLE_CLAUDE_RESPONSE)

    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'), \
         patch('anthropic.Anthropic', return_value=mock_client):
        import session_end, importlib
        importlib.reload(session_end)
        stdin = json.dumps({'session_id': 'x', 'cwd': '/fake/myproject'})
        with patch('sys.stdin', io.StringIO(stdin)):
            with patch('sys.stdout', io.StringIO()):
                session_end.main()

    return notesmd_calls, mock_client


def test_session_end_reads_wip():
    calls, _ = run_hook()
    assert any('print' in c and 'wip.md' in str(c) for c in calls)


def test_session_end_calls_claude_api():
    _, mock_client = run_hook()
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs['model'] == 'claude-haiku-4-5-20251001'


def test_session_end_writes_session_note():
    calls, _ = run_hook()
    create_calls = [c for c in calls if 'create' in c and '.md' in str(c) and 'wip' not in str(c) and '--overwrite' in c]
    session_note_call = next(
        (c for c in create_calls if 'sessions/' in str(c) and '2026-06-21-myproject' in str(c)),
        None
    )
    assert session_note_call is not None


def test_session_end_updates_project_page():
    calls, _ = run_hook()
    project_call = next(
        (c for c in calls if 'create' in c and 'projects/myproject/PROJECT.md' in str(c)),
        None
    )
    assert project_call is not None


def test_session_end_renames_wip():
    calls, _ = run_hook()
    move_call = next(
        (c for c in calls if 'move' in c and 'wip.md' in str(c)),
        None
    )
    assert move_call is not None
    assert '2026-06-21-myproject.wip.md' in str(move_call)
    assert '2026-06-21-myproject.md' in str(move_call)


def test_session_end_skips_if_no_wip():
    calls, mock_client = run_hook(wip_content='')
    mock_client.messages.create.assert_not_called()
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/test_session_end.py -v
```

Expected: `ModuleNotFoundError: No module named 'session_end'`

- [ ] **Step 3: Write src/hooks/session-end.py**

```python
#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
import common
import anthropic

SYSTEM_PROMPT = """You process raw session logs for an agent memory vault.
Output ONLY valid JSON with no markdown fences. Facts only — no speculation."""

USER_PROMPT_TEMPLATE = """WIP session log:
{wip_content}

Current PROJECT.md (may be empty for new projects):
{project_content}

Generate a JSON object with these keys:
- "session_note": markdown string, max 300 words. Sections: "## What was worked on", "## Decisions made", "## Open questions"
- "current_focus": one sentence describing what is being worked on now
- "decisions": list of strings, key decisions made (empty list if none)
- "index_line": one sentence status + "Last session: {date}."

Output only the JSON object, no other text."""


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    cwd = data.get('cwd', os.getcwd())
    project = common.get_project_name(cwd)
    today = common.today()
    wip = common.wip_path(project, today)

    wip_content = common.run_notesmd(['print', wip])
    if not wip_content.strip():
        return

    project_page = f'projects/{project}/PROJECT.md'
    project_content = common.run_notesmd(['print', project_page])

    client = anthropic.Anthropic()
    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            'role': 'user',
            'content': USER_PROMPT_TEMPLATE.format(
                wip_content=wip_content,
                project_content=project_content or '(no existing project page)',
                date=today,
            )
        }]
    )

    try:
        result = json.loads(message.content[0].text)
    except (json.JSONDecodeError, IndexError, AttributeError):
        return

    session_note_path = common.session_path(project, today)
    note_frontmatter = f'---\nproject: {project}\ndate: {today}\nagent: claude-code\n---\n\n'
    common.run_notesmd([
        'create', session_note_path,
        '--content', note_frontmatter + result.get('session_note', ''),
        '--overwrite',
    ])

    decisions_md = '\n'.join(f'- {d}' for d in result.get('decisions', []))
    project_body = (
        f'---\nname: {project}\npath: {cwd}\nstatus: active\nlast_session: {today}\n---\n\n'
        f'## Current focus\n{result.get("current_focus", "")}\n\n'
        f'## Key decisions\n{decisions_md}\n'
    )
    common.run_notesmd(['create', project_page, '--content', project_body, '--overwrite'])

    index_entry = f'\n## {project}\nPath: {cwd} | Status: active\n{result.get("index_line", "")}\n'
    index_content = common.run_notesmd(['print', 'projects/index.md'])
    if f'## {project}' in index_content:
        lines = index_content.split('\n')
        new_lines = []
        skip = False
        for line in lines:
            if line.startswith(f'## {project}'):
                skip = True
                new_lines.append(f'## {project}')
                new_lines.append(f'Path: {cwd} | Status: active')
                new_lines.append(result.get('index_line', ''))
            elif skip and line.startswith('## '):
                skip = False
                new_lines.append(line)
            elif not skip:
                new_lines.append(line)
        common.run_notesmd(['create', 'projects/index.md', '--content', '\n'.join(new_lines), '--overwrite'])
    else:
        common.run_notesmd(['create', 'projects/index.md', '--content', index_entry, '--append'])

    clean_wip = common.session_path(project, today)
    common.run_notesmd(['move', wip, clean_wip])


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_session_end.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks/session-end.py tests/test_session_end.py
git commit -m "feat: session-end hook with Claude API processing"
```

---

## Task 7: SKILL.md — teach Claude how to use the vault

**Files:**
- Create: `src/skills/agent-memory/SKILL.md`

**Interfaces:**
- Produces: skill loaded by Claude Code at session start; instructs Claude's behaviour

- [ ] **Step 1: Create src/skills/agent-memory/SKILL.md**

```markdown
---
name: agent-memory
description: Persistent cross-project memory vault in Obsidian. Loaded proactively at every session to orient the agent.
when: always
---

# Agent Memory

You have access to a persistent memory vault at `~/Documents/AgentMemory` (or `$AGENT_MEMORY_VAULT`).
This vault stores your memory across sessions and projects. It is written by you, not by the user.

## At session start (proactive)

The SessionStart hook has already injected `projects/index.md` and the current project page into
your context above. Read them — they tell you what has been worked on recently across all projects.

If you do not see vault context above, read it yourself:

```bash
notesmd-cli print "projects/index.md" --vault "AgentMemory"
notesmd-cli print "projects/<current-project>/PROJECT.md" --vault "AgentMemory"
```

## During a session

**Read from the vault when:**
- The user asks what has been worked on recently or across projects
- You need context about a project you haven't seen yet this session
- You want to check for prior decisions before suggesting an approach

**Do not write during a session.** The hooks handle all writes. You only read mid-session.

**To search the vault:**
```bash
notesmd-cli search-content "search term" --format json --vault "AgentMemory"
```

## Rules

1. **Facts only.** Never write speculation. Only record what directly happened or was decided.
2. **No secrets.** Never write credentials, tokens, passwords, or sensitive data to the vault.
3. **Contradiction rule.** If the vault says X and the live codebase says Y, trust the codebase.
   Flag the conflict clearly and note it for the session-end update.
4. **Repo truth wins.** Vault notes about code are summaries — the codebase is the source of truth.

## What belongs in this vault vs native Claude memory

- **Native Claude memory** (`~/.claude/projects/.../memory/`): facts about the *user* — preferences,
  feedback, working conventions.
- **AgentMemory vault**: facts about the *work* — project state, session history, cross-project patterns.
```

- [ ] **Step 2: Verify skill file is valid markdown**

```bash
python3 -c "
with open('src/skills/agent-memory/SKILL.md') as f:
    content = f.read()
assert '---' in content
assert 'agent-memory' in content
assert 'notesmd-cli' in content
print('skill file ok')
"
```

Expected: `skill file ok`

- [ ] **Step 3: Commit**

```bash
git add src/skills/
git commit -m "feat: agent-memory skill"
```

---

## Task 8: install.py — deploy everything and wire Claude Code

**Files:**
- Create: `install.py`

This script: installs the vault template, registers it with notesmd-cli, deploys hooks and skill to `~/.claude/`, merges hooks into `~/.claude/settings.json`, and adds the skill to chezmoi.

- [ ] **Step 1: Run the full test suite first**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests PASS. Fix any failures before continuing.

- [ ] **Step 2: Create install.py**

```python
#!/usr/bin/env python3
"""Deploy agent-memory hooks, skill, and vault to ~/.claude/ and ~/Documents/AgentMemory."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
VAULT_PATH = Path(os.environ.get('AGENT_MEMORY_VAULT', Path.home() / 'Documents' / 'AgentMemory'))
CLAUDE_DIR = Path.home() / '.claude'
HOOKS_DEST = CLAUDE_DIR / 'hooks' / 'agent-memory'
SKILL_DEST = CLAUDE_DIR / 'skills' / 'agent-memory'
SETTINGS_PATH = CLAUDE_DIR / 'settings.json'

HOOK_ENTRIES = {
    'SessionStart': [{
        'hooks': [{'type': 'command', 'command': f'python3 {HOOKS_DEST}/session-start.py'}]
    }],
    'PostToolUse': [{
        'matcher': 'Edit|Write',
        'hooks': [{'type': 'command', 'command': f'python3 {HOOKS_DEST}/post-tool-use.py'}]
    }],
    'PreCompact': [{
        'hooks': [{'type': 'command', 'command': f'python3 {HOOKS_DEST}/pre-compact.py'}]
    }],
    'SessionEnd': [{
        'hooks': [{'type': 'command', 'command': f'python3 {HOOKS_DEST}/session-end.py'}]
    }],
}


def run(cmd, **kwargs):
    print(f'  $ {" ".join(str(c) for c in cmd)}')
    result = subprocess.run(cmd, check=True, **kwargs)
    return result


def deploy_hooks():
    print('\n[1] Deploying hook scripts...')
    HOOKS_DEST.mkdir(parents=True, exist_ok=True)
    for f in (REPO_ROOT / 'src' / 'hooks').glob('*.py'):
        shutil.copy2(f, HOOKS_DEST / f.name)
        print(f'  copied {f.name}')


def deploy_skill():
    print('\n[2] Deploying skill...')
    SKILL_DEST.mkdir(parents=True, exist_ok=True)
    src = REPO_ROOT / 'src' / 'skills' / 'agent-memory' / 'SKILL.md'
    shutil.copy2(src, SKILL_DEST / 'SKILL.md')
    print(f'  copied SKILL.md')


def wire_hooks():
    print('\n[3] Wiring hooks into ~/.claude/settings.json...')
    settings = json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.exists() else {}
    hooks = settings.setdefault('hooks', {})
    for event, entries in HOOK_ENTRIES.items():
        if event not in hooks:
            hooks[event] = entries
            print(f'  added {event}')
        else:
            print(f'  skipped {event} (already configured)')
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def bootstrap_vault():
    print('\n[4] Bootstrapping vault...')
    vault_src = REPO_ROOT / 'src' / 'vault'
    for src_file in vault_src.rglob('*'):
        if src_file.is_file():
            rel = src_file.relative_to(vault_src)
            dest = VAULT_PATH / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(src_file, dest)
                print(f'  created {rel}')
            else:
                print(f'  skipped {rel} (already exists)')


def register_vault():
    print('\n[5] Registering vault with notesmd-cli...')
    result = subprocess.run(
        ['notesmd-cli', 'list-vaults', '--path-only'],
        capture_output=True, text=True
    )
    if str(VAULT_PATH) in result.stdout:
        print(f'  vault already registered at {VAULT_PATH}')
        return
    run(['notesmd-cli', 'add-vault', str(VAULT_PATH), '--set-default'])


def add_to_chezmoi():
    print('\n[6] Adding skill to chezmoi...')
    try:
        run(['chezmoi', 'add', str(SKILL_DEST / 'SKILL.md')])
    except subprocess.CalledProcessError:
        print('  chezmoi add failed — add manually if needed')


if __name__ == '__main__':
    print(f'Installing agent-memory to {CLAUDE_DIR}')
    print(f'Vault: {VAULT_PATH}')
    deploy_hooks()
    deploy_skill()
    wire_hooks()
    bootstrap_vault()
    register_vault()
    add_to_chezmoi()
    print('\nDone. Start a new Claude Code session to activate.')
```

- [ ] **Step 3: Run the installer**

```bash
python3 install.py
```

Expected output (approximately):
```
Installing agent-memory to /Users/charlie/.claude
Vault: /Users/charlie/Documents/AgentMemory

[1] Deploying hook scripts...
  copied common.py
  copied session-start.py
  copied post-tool-use.py
  copied pre-compact.py
  copied session-end.py

[2] Deploying skill...
  copied SKILL.md

[3] Wiring hooks into ~/.claude/settings.json...
  added SessionStart
  added PostToolUse
  added PreCompact
  added SessionEnd

[4] Bootstrapping vault...
  created VAULT_RULES.md
  created projects/index.md
  created global/patterns.md
  created global/entities.md

[5] Registering vault with notesmd-cli...
  $ notesmd-cli add-vault /Users/charlie/Documents/AgentMemory --set-default

[6] Adding skill to chezmoi...
  $ chezmoi add /Users/charlie/.claude/skills/agent-memory/SKILL.md

Done. Start a new Claude Code session to activate.
```

- [ ] **Step 4: Verify installation**

```bash
# hooks deployed
ls ~/.claude/hooks/agent-memory/

# skill deployed
ls ~/.claude/skills/agent-memory/

# hooks in settings
python3 -c "import json; s=json.load(open('$HOME/.claude/settings.json')); print(list(s['hooks'].keys()))"

# vault registered
notesmd-cli list-vaults

# vault structure
notesmd-cli list --vault "AgentMemory"
```

Expected:
- Hook scripts present: `common.py session-start.py post-tool-use.py pre-compact.py session-end.py`
- Skill present: `SKILL.md`
- Settings keys include: `['SessionStart', 'PostToolUse', 'PreCompact', 'SessionEnd', ...]`
- AgentMemory listed as a vault
- Vault shows `VAULT_RULES.md`, `projects/`, `global/`

- [ ] **Step 5: Smoke test — start a new session**

Open a new Claude Code session in any project directory. Verify:
1. The agent greets you with vault context (projects/index.md content) injected
2. Edit any file — check that the WIP file is created and updated:
   ```bash
   notesmd-cli list "sessions" --vault "AgentMemory"
   notesmd-cli print "sessions/2026/06/$(date +%Y-%m-%d)-$(basename $(git rev-parse --show-toplevel 2>/dev/null || pwd)).wip.md" --vault "AgentMemory"
   ```
3. End the session normally. Check that:
   - WIP file was renamed to `.md`
   - `projects/<name>/PROJECT.md` was created/updated
   - `projects/index.md` has an entry for this project

- [ ] **Step 6: Add hooks to chezmoi**

```bash
chezmoi add ~/.claude/hooks/agent-memory/common.py
chezmoi add ~/.claude/hooks/agent-memory/session-start.py
chezmoi add ~/.claude/hooks/agent-memory/post-tool-use.py
chezmoi add ~/.claude/hooks/agent-memory/pre-compact.py
chezmoi add ~/.claude/hooks/agent-memory/session-end.py
chezmoi add ~/.claude/settings.json
```

- [ ] **Step 7: Final commit**

```bash
git add install.py
git commit -m "feat: install script for agent-memory system"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Vault structure (VAULT_RULES.md, projects/index.md, global/, sessions/) — Task 1
- ✅ notesmd-cli as sole vault interface — all hooks use `common.run_notesmd`
- ✅ SessionStart hook reads index + project page — Task 3
- ✅ PostToolUse hook (Edit/Write filter) appends to WIP — Task 4
- ✅ PreCompact hook checkpoints WIP — Task 5
- ✅ SessionEnd hook calls Claude API, writes clean note, updates PROJECT.md and index.md — Task 6
- ✅ Dumb hooks (0 tokens during session) — Tasks 3–5 make no API calls
- ✅ `.wip.md` pattern for interrupted sessions — Task 6 renames on success, leaves on failure
- ✅ Project name from `git rev-parse` with basename fallback — Task 2
- ✅ Skill teaches Claude what/when/how to read vault — Task 7
- ✅ Hooks wired into settings.json — Task 8
- ✅ Skill and hooks added to chezmoi — Task 8
- ✅ `ANTHROPIC_API_KEY` env var required noted — Global Constraints

**Placeholder scan:** No TBD/TODO. All test code is complete. All implementation code is complete.

**Type consistency:** `wip_path` and `session_path` return `str` in Task 2 and are called as `str` in Tasks 3–6. `get_project_name` returns `str` throughout. `run_notesmd` returns `str` throughout. ✅
