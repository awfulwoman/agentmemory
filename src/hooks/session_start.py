#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def _extract_current_focus(project_content: str) -> str:
    m = re.search(r'## Current focus\s*\n(.*?)(?=\n## |\Z)', project_content, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ''


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    cwd = data.get('cwd', os.getcwd())
    project = common.get_project_name(cwd)
    today = common.today()

    index_content = common.read_note('projects/index.md')
    project_content = common.read_note(f'projects/{project}/PROJECT.md')

    timestamp = datetime.now().strftime('%H:%M')
    wip_header = (
        f'---\nproject: {project}\ndate: {today}\nagent: claude-code\nstatus: wip\n---\n\n'
        f'[{timestamp}] Session started\n'
    )
    common.append_wip(project, today, wip_header)

    context_parts = []
    if index_content.strip():
        context_parts.append('## Agent Memory: All Projects\n\n' + index_content.strip())
    if project_content.strip():
        context_parts.append(f'## Agent Memory: {project}\n\n' + project_content.strip())

    out: dict = {}
    if context_parts:
        out['hookSpecificOutput'] = {
            'hookEventName': 'SessionStart',
            'additionalContext': '\n\n'.join(context_parts),
        }

    focus = _extract_current_focus(project_content)
    if focus:
        out['terminalSequence'] = f'\033]9;{project}: {focus}\007'

    if out:
        print(json.dumps(out))


if __name__ == '__main__':
    main()
