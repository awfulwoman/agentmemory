#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

PROMPT = """\
You process raw session logs for an agent memory vault.
Output ONLY valid JSON with no markdown fences. Facts only — no speculation.

WIP session log:
{wip_content}

Current PROJECT.md (may be empty for new projects):
{project_content}

Generate a JSON object with these keys:
- "session_note": markdown string, max 300 words. Sections: "## What was worked on", "## Decisions made", "## Open questions"
- "current_focus": one sentence describing what is being worked on now
- "decisions": list of strings, key decisions made (empty list if none)
- "index_line": one sentence status + "Last session: {date}."

Output only the JSON object, no other text.\
"""


def _update_index(project: str, cwd: str, index_line: str) -> None:
    index_content = common.read_note('projects/index.md')
    entry = f'## {project}\nPath: {cwd} | Status: active\n{index_line}\n'

    if f'## {project}' in index_content:
        lines = index_content.split('\n')
        new_lines, skip = [], False
        for line in lines:
            if line.startswith(f'## {project}'):
                skip = True
                new_lines += [f'## {project}', f'Path: {cwd} | Status: active', index_line]
            elif skip and line.startswith('## '):
                skip = False
                new_lines.append(line)
            elif not skip:
                new_lines.append(line)
        common.write_note('projects/index.md', '\n'.join(new_lines))
    else:
        common.append_note('projects/index.md', '\n' + entry)


def process(data: dict) -> None:
    cwd = data.get('cwd', os.getcwd())
    project = common.get_project_name(cwd)
    today = common.find_wip(project) or common.today()

    wip_content = common.read_wip(project, today)
    if not wip_content.strip():
        return

    project_page = f'projects/{project}/PROJECT.md'
    project_content = common.read_note(project_page)

    result_raw = subprocess.run(
        ['claude', '--model', 'claude-haiku-4-5-20251001', '-p',
         PROMPT.format(
             wip_content=wip_content,
             project_content=project_content or '(no existing project page)',
             date=today,
         )],
        capture_output=True, text=True, timeout=60,
    )

    text = re.sub(r'^```(?:json)?\s*', '', result_raw.stdout.strip())
    text = re.sub(r'\s*```$', '', text)
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return

    session_note_path = common.session_path(project, today)
    frontmatter = f'---\nproject: {project}\ndate: {today}\nagent: claude-code\n---\n\n'
    common.write_note(session_note_path, frontmatter + result.get('session_note', ''))

    decisions_md = '\n'.join(f'- {d}' for d in result.get('decisions', []))
    project_body = (
        f'---\nname: {project}\npath: {cwd}\nstatus: active\nlast_session: {today}\n---\n\n'
        f'## Current focus\n{result.get("current_focus", "")}\n\n'
        f'## Key decisions\n{decisions_md}\n'
    )
    common.write_note(project_page, project_body)

    _update_index(project, cwd, result.get('index_line', ''))

    common.delete_wip(project, today)


def hook_mode() -> None:
    """Read stdin from Claude Code and spawn a detached background processor."""
    raw = sys.stdin.read()
    try:
        json.loads(raw)  # validate before writing
    except json.JSONDecodeError:
        return

    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w')
    tf.write(raw)
    tf.close()

    log = open('/tmp/agent-memory-session-end.log', 'a')
    subprocess.Popen(
        [sys.executable, __file__, tf.name],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=log,
    )


def processor_mode(tmp_path: str) -> None:
    """Background processor: read temp file, call Claude, update vault."""
    with open(tmp_path) as f:
        data = json.load(f)
    os.unlink(tmp_path)
    process(data)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        processor_mode(sys.argv[1])
    else:
        hook_mode()
