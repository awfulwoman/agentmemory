#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import anthropic

SYSTEM_PROMPT = (
    'You process raw session logs for an agent memory vault. '
    'Output ONLY valid JSON with no markdown fences. Facts only — no speculation.'
)

USER_PROMPT = """\
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
    index_content = common.run_notesmd(['print', 'projects/index.md'])
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
        common.run_notesmd([
            'create', 'projects/index.md',
            '--content', '\n'.join(new_lines),
            '--overwrite',
        ])
    else:
        common.run_notesmd(['create', 'projects/index.md', '--content', '\n' + entry, '--append'])


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
            'content': USER_PROMPT.format(
                wip_content=wip_content,
                project_content=project_content or '(no existing project page)',
                date=today,
            ),
        }],
    )

    try:
        result = json.loads(message.content[0].text)
    except (json.JSONDecodeError, IndexError, AttributeError):
        return

    session_note_path = common.session_path(project, today)
    frontmatter = f'---\nproject: {project}\ndate: {today}\nagent: claude-code\n---\n\n'
    common.run_notesmd([
        'create', session_note_path,
        '--content', frontmatter + result.get('session_note', ''),
        '--overwrite',
    ])

    decisions_md = '\n'.join(f'- {d}' for d in result.get('decisions', []))
    project_body = (
        f'---\nname: {project}\npath: {cwd}\nstatus: active\nlast_session: {today}\n---\n\n'
        f'## Current focus\n{result.get("current_focus", "")}\n\n'
        f'## Key decisions\n{decisions_md}\n'
    )
    common.run_notesmd(['create', project_page, '--content', project_body, '--overwrite'])

    _update_index(project, cwd, result.get('index_line', ''))

    common.run_notesmd(['delete', wip])


if __name__ == '__main__':
    main()
