import json
import sys
import io
import os
from unittest.mock import patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'hooks'))


def run_hook(stdin_data: dict) -> list:
    notesmd_calls = []

    def mock_notesmd(args):
        notesmd_calls.append(list(args))
        return ''

    import post_tool_use
    import importlib
    importlib.reload(post_tool_use)

    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'), \
         patch('sys.stdin', io.StringIO(json.dumps(stdin_data))), \
         patch('sys.stdout', io.StringIO()):
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


def test_bash_tool_ignored():
    calls = run_hook({
        'session_id': 'x',
        'tool_name': 'Bash',
        'tool_input': {'command': 'git commit -m "test"'},
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
    append_call = next(c for c in calls if '--append' in c)
    assert 'sessions/2026/06/2026-06-21-myproject.wip.md' in str(append_call)


def test_handles_invalid_json():
    import post_tool_use, importlib
    importlib.reload(post_tool_use)
    with patch('sys.stdin', io.StringIO('not json')), \
         patch('sys.stdout', io.StringIO()):
        post_tool_use.main()
