#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

MIN_LENGTH = 20
TRUNCATE_AT = 300


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    prompt = data.get('prompt', '').strip()
    if len(prompt) < MIN_LENGTH:
        return

    cwd = data.get('cwd', os.getcwd())
    project = common.get_project_name(cwd)
    session_date = common.find_wip(project) or common.today()

    text = prompt if len(prompt) <= TRUNCATE_AT else prompt[:TRUNCATE_AT] + '…'
    timestamp = datetime.now().strftime('%H:%M')
    common.append_wip(project, session_date, f'[{timestamp}] user: {text}\n')


if __name__ == '__main__':
    main()
