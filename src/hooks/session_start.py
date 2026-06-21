#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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

    index_content = common.run_notesmd(['print', 'projects/index.md'])
    project_content = common.run_notesmd(['print', f'projects/{project}/PROJECT.md'])

    wip = common.wip_path(project, today)
    timestamp = datetime.now().strftime('%H:%M')
    wip_header = (
        f'---\nproject: {project}\ndate: {today}\nagent: claude-code\nstatus: wip\n---\n\n'
        f'[{timestamp}] Session started\n'
    )
    common.run_notesmd(['create', wip, '--content', wip_header])

    output_parts = []
    if index_content.strip():
        output_parts.append('## Agent Memory: All Projects\n\n' + index_content.strip())
    if project_content.strip():
        output_parts.append(f'## Agent Memory: {project}\n\n' + project_content.strip())

    if output_parts:
        print('\n\n'.join(output_parts))


if __name__ == '__main__':
    main()
