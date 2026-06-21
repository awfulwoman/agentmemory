import os
import sys
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'hooks'))
import common


def test_get_vault_path_from_env(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        assert common.get_vault_path() == str(tmp_path)


def test_get_vault_path_default():
    env = {k: v for k, v in os.environ.items() if k != 'AGENT_MEMORY_VAULT'}
    with patch.dict(os.environ, env, clear=True):
        result = common.get_vault_path()
        assert result == os.path.expanduser('~/Documents/Personal/AgentMemory')


def test_get_project_name_from_git(tmp_path):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='/Users/charlie/Code/awfulwoman/myproject\n'
        )
        result = common.get_project_name(str(tmp_path))
        assert result == 'myproject'


def test_get_project_name_fallback_basename(tmp_path):
    project_dir = tmp_path / 'my-project'
    project_dir.mkdir()
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        result = common.get_project_name(str(project_dir))
        assert result == 'my-project'


def test_read_note_returns_content(tmp_path):
    (tmp_path / 'projects').mkdir()
    (tmp_path / 'projects' / 'index.md').write_text('hello')
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        assert common.read_note('projects/index.md') == 'hello'


def test_read_note_missing_returns_empty(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        assert common.read_note('projects/missing.md') == ''


def test_write_note_creates_dirs_and_file(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        common.write_note('a/b/note.md', 'content')
    assert (tmp_path / 'a' / 'b' / 'note.md').read_text() == 'content'


def test_append_note_creates_and_appends(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        common.append_note('notes/log.md', 'line1\n')
        common.append_note('notes/log.md', 'line2\n')
    assert (tmp_path / 'notes' / 'log.md').read_text() == 'line1\nline2\n'


def test_wip_path():
    path = common.wip_path('myproject', '2026-06-21')
    assert path == 'sessions/2026/06/2026-06-21-myproject.wip.md'


def test_session_path():
    path = common.session_path('myproject', '2026-06-21')
    assert path == 'sessions/2026/06/2026-06-21-myproject.md'


def test_read_wip_missing_returns_empty(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        assert common.read_wip('proj', '2026-06-21') == ''


def test_append_and_delete_wip(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        common.append_wip('proj', '2026-06-21', '[10:00] edit: foo.py\n')
        assert common.read_wip('proj', '2026-06-21') == '[10:00] edit: foo.py\n'
        common.delete_wip('proj', '2026-06-21')
        assert common.read_wip('proj', '2026-06-21') == ''


def test_find_wip_returns_none_when_absent(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        assert common.find_wip('proj') is None


def test_find_wip_returns_date_of_existing_file(tmp_path):
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        common.append_wip('proj', '2026-06-21', 'line\n')
        assert common.find_wip('proj') == '2026-06-21'


def test_find_wip_returns_newest_when_multiple(tmp_path):
    import time
    with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': str(tmp_path)}):
        common.append_wip('proj', '2026-06-20', 'older\n')
        time.sleep(0.01)
        common.append_wip('proj', '2026-06-21', 'newer\n')
        assert common.find_wip('proj') == '2026-06-21'
