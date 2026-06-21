import os
import subprocess
from datetime import date


def get_vault_path() -> str:
    return os.environ.get('AGENT_MEMORY_VAULT', os.path.expanduser('~/Documents/AgentMemory'))


def get_vault_name() -> str:
    return os.path.basename(get_vault_path())


def get_project_name(cwd: str) -> str:
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=2,
    )
    if result.returncode == 0 and result.stdout.strip():
        return os.path.basename(result.stdout.strip())
    return os.path.basename(cwd.rstrip('/'))


def run_notesmd(args: list[str]) -> str:
    cmd = ['notesmd-cli'] + args + ['--vault', get_vault_name()]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result.stdout


def wip_path(project: str, session_date: str) -> str:
    year, month, _ = session_date.split('-')
    return f'sessions/{year}/{month}/{session_date}-{project}.wip.md'


def session_path(project: str, session_date: str) -> str:
    year, month, _ = session_date.split('-')
    return f'sessions/{year}/{month}/{session_date}-{project}.md'


def today() -> str:
    return date.today().isoformat()
