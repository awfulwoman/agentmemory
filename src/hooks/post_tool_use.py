#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
