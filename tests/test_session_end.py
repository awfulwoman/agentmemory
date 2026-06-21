import json
import sys
import io
import os
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'hooks'))

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
    'session_note': '## What was worked on\nEdited memory.py and tests.\n\n## Decisions made\nUsed append mode.\n\n## Open questions\nNone.',
    'current_focus': 'Implementing session-end hook.',
    'decisions': ['Used append mode for WIP files'],
    'index_line': 'Implementing agent memory hooks. Last session: 2026-06-21.',
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

    import session_end
    import importlib
    importlib.reload(session_end)

    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'), \
         patch('anthropic.Anthropic', return_value=mock_client), \
         patch('sys.stdin', io.StringIO(json.dumps({'session_id': 'x', 'cwd': '/fake/myproject'}))), \
         patch('sys.stdout', io.StringIO()):
        session_end.main()

    return notesmd_calls, mock_client


def test_reads_wip_file():
    calls, _ = run_hook()
    assert any('print' in c and 'wip.md' in str(c) for c in calls)


def test_calls_claude_api_with_haiku():
    _, mock_client = run_hook()
    mock_client.messages.create.assert_called_once()
    kwargs = mock_client.messages.create.call_args[1]
    assert kwargs['model'] == 'claude-haiku-4-5-20251001'


def test_writes_clean_session_note():
    calls, _ = run_hook()
    note_call = next(
        (c for c in calls
         if 'create' in c
         and 'sessions/2026/06/2026-06-21-myproject.md' in str(c)
         and 'wip' not in str(c)
         and '--overwrite' in c),
        None,
    )
    assert note_call is not None


def test_updates_project_page():
    calls, _ = run_hook()
    project_call = next(
        (c for c in calls if 'create' in c and 'projects/myproject/PROJECT.md' in str(c)),
        None,
    )
    assert project_call is not None


def test_deletes_wip_file():
    calls, _ = run_hook()
    delete_call = next(
        (c for c in calls if 'delete' in c and 'wip.md' in str(c)),
        None,
    )
    assert delete_call is not None, f'No delete wip call found in: {calls}'


def test_skips_if_no_wip():
    calls, mock_client = run_hook(wip_content='')
    mock_client.messages.create.assert_not_called()


def test_appends_to_index_when_project_not_present():
    calls, _ = run_hook(index_content='# Projects Index\n')
    append_call = next(
        (c for c in calls if 'create' in c and 'index.md' in str(c) and '--append' in c),
        None,
    )
    assert append_call is not None


def test_updates_existing_project_in_index():
    existing_index = '# Projects Index\n\n## myproject\nPath: /old | Status: active\nOld status. Last session: 2026-06-01.\n'
    calls, _ = run_hook(index_content=existing_index)
    overwrite_call = next(
        (c for c in calls if 'create' in c and 'index.md' in str(c) and '--overwrite' in c),
        None,
    )
    assert overwrite_call is not None
