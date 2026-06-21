import json
import sys
import io
import os
from unittest.mock import patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'hooks'))


def run_hook(stdin_data: dict, notesmd_responses: dict = None) -> tuple[str, list]:
    notesmd_calls = []
    responses = notesmd_responses or {}

    def mock_notesmd(args):
        notesmd_calls.append(list(args))
        for key, val in responses.items():
            if key in str(args):
                return val
        return ''

    import session_start
    import importlib
    importlib.reload(session_start)

    captured = io.StringIO()
    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'), \
         patch('sys.stdin', io.StringIO(json.dumps(stdin_data))), \
         patch('sys.stdout', captured):
        session_start.main()

    return captured.getvalue(), notesmd_calls


def test_reads_projects_index():
    _, calls = run_hook(
        {'session_id': 'x', 'cwd': '/fake/myproject'},
        {'index.md': '## myproject\nStatus: active\n'},
    )
    assert any('projects/index.md' in str(c) and 'print' in c for c in calls)


def test_injects_index_content_to_stdout():
    output, _ = run_hook(
        {'session_id': 'x', 'cwd': '/fake/myproject'},
        {'index.md': '## myproject\nStatus: active\n'},
    )
    assert 'myproject' in output
    assert 'Status: active' in output


def test_reads_project_page_when_exists():
    _, calls = run_hook(
        {'session_id': 'x', 'cwd': '/fake/myproject'},
        {'PROJECT.md': '## Current focus\nBuilding hooks.\n'},
    )
    assert any('projects/myproject/PROJECT.md' in str(c) for c in calls)


def test_creates_wip_file():
    _, calls = run_hook({'session_id': 'x', 'cwd': '/fake/myproject'})
    create_call = next(
        (c for c in calls if 'create' in c and 'wip.md' in str(c)),
        None,
    )
    assert create_call is not None, f'No create wip call in: {calls}'
    assert 'sessions/2026/06/2026-06-21-myproject.wip.md' in str(create_call)


def test_wip_content_has_project_and_timestamp():
    _, calls = run_hook({'session_id': 'x', 'cwd': '/fake/myproject'})
    create_call = next(c for c in calls if 'create' in c and 'wip.md' in str(c))
    content_idx = create_call.index('--content') + 1
    content = create_call[content_idx]
    assert 'myproject' in content
    assert 'Session started' in content


def test_handles_missing_project_page_gracefully():
    output, calls = run_hook(
        {'session_id': 'x', 'cwd': '/fake/myproject'},
        {'index.md': '## myproject\n'},
    )
    assert output is not None


def test_handles_invalid_json_gracefully():
    import session_start, importlib
    importlib.reload(session_start)
    with patch('sys.stdin', io.StringIO('not json')), \
         patch('sys.stdout', io.StringIO()):
        session_start.main()
