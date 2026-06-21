import json
import sys
import io
import os
from unittest.mock import patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'hooks'))


def run_hook(cwd='/fake/myproject') -> list:
    notesmd_calls = []

    def mock_notesmd(args):
        notesmd_calls.append(list(args))
        return ''

    import pre_compact
    import importlib
    importlib.reload(pre_compact)

    stdin = json.dumps({'session_id': 'x', 'cwd': cwd})
    with patch('common.run_notesmd', side_effect=mock_notesmd), \
         patch('common.get_project_name', return_value='myproject'), \
         patch('common.today', return_value='2026-06-21'), \
         patch('sys.stdin', io.StringIO(stdin)), \
         patch('sys.stdout', io.StringIO()):
        pre_compact.main()

    return notesmd_calls


def test_appends_checkpoint():
    calls = run_hook()
    append_call = next((c for c in calls if '--append' in c), None)
    assert append_call is not None
    content = append_call[append_call.index('--content') + 1]
    assert 'compact' in content.lower() or 'checkpoint' in content.lower()


def test_targets_wip_file():
    calls = run_hook()
    append_call = next(c for c in calls if '--append' in c)
    assert 'sessions/2026/06/2026-06-21-myproject.wip.md' in str(append_call)


def test_handles_invalid_json():
    import pre_compact, importlib
    importlib.reload(pre_compact)
    with patch('sys.stdin', io.StringIO('not json')), \
         patch('sys.stdout', io.StringIO()):
        pre_compact.main()
