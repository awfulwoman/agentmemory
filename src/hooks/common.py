import glob
import os
import subprocess
from datetime import date


def get_vault_path() -> str:
    return os.environ.get('AGENT_MEMORY_VAULT', os.path.expanduser('~/Documents/Personal/AgentMemory'))


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


def wip_path(project: str, session_date: str) -> str:
    year, month, _ = session_date.split('-')
    return f'sessions/{year}/{month}/{session_date}-{project}.wip.md'


def session_path(project: str, session_date: str) -> str:
    year, month, _ = session_date.split('-')
    return f'sessions/{year}/{month}/{session_date}-{project}.md'


def today() -> str:
    return date.today().isoformat()


# Vault note helpers — direct filesystem access, no external dependencies.

def _note_path(rel_path: str) -> str:
    return os.path.join(get_vault_path(), rel_path)


def read_note(rel_path: str) -> str:
    try:
        with open(_note_path(rel_path)) as f:
            return f.read()
    except FileNotFoundError:
        return ''


def write_note(rel_path: str, content: str) -> None:
    path = _note_path(rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)


def append_note(rel_path: str, content: str) -> None:
    path = _note_path(rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a') as f:
        f.write(content)


# WIP helpers — same pattern, separate names for clarity.

def wip_full_path(project: str, session_date: str) -> str:
    return _note_path(wip_path(project, session_date))


def read_wip(project: str, session_date: str) -> str:
    try:
        with open(wip_full_path(project, session_date)) as f:
            return f.read()
    except FileNotFoundError:
        return ''


def append_wip(project: str, session_date: str, line: str) -> None:
    path = wip_full_path(project, session_date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a') as f:
        f.write(line)


def delete_wip(project: str, session_date: str) -> None:
    try:
        os.remove(wip_full_path(project, session_date))
    except FileNotFoundError:
        pass


def find_wip(project: str) -> str | None:
    """Return the date string of the most recently modified WIP file for project, or None."""
    pattern = os.path.join(get_vault_path(), f'sessions/*/*/????-??-??-{project}.wip.md')
    matches = glob.glob(pattern)
    if not matches:
        return None
    newest = max(matches, key=os.path.getmtime)
    basename = os.path.basename(newest)
    return basename[:10]  # YYYY-MM-DD
