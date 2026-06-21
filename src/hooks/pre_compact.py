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
    session_date = common.find_wip(project) or common.today()

    timestamp = datetime.now().strftime('%H:%M')
    line = f'[{timestamp}] ---pre-compact checkpoint---\n'
    common.append_wip(project, session_date, line)


if __name__ == '__main__':
    main()
