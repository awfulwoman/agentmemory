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
        assert result == os.path.expanduser('~/Documents/AgentMemory')


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


def test_run_notesmd_returns_stdout():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='note content\n')
        result = common.run_notesmd(['print', 'projects/index.md'])
        assert result == 'note content\n'
        args = mock_run.call_args[0][0]
        assert args[0] == 'notesmd-cli'
        assert 'print' in args
        assert 'projects/index.md' in args


def test_run_notesmd_includes_vault_flag():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout='')
        with patch.dict(os.environ, {'AGENT_MEMORY_VAULT': '/fake/AgentMemory'}):
            common.run_notesmd(['list'])
        args = mock_run.call_args[0][0]
        assert '--vault' in args
        assert 'AgentMemory' in args


def test_wip_path():
    path = common.wip_path('myproject', '2026-06-21')
    assert path == 'sessions/2026/06/2026-06-21-myproject.wip.md'


def test_session_path():
    path = common.session_path('myproject', '2026-06-21')
    assert path == 'sessions/2026/06/2026-06-21-myproject.md'
