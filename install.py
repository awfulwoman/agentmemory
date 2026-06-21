#!/usr/bin/env python3
"""Deploy agent-memory hooks, skill, and vault to ~/.claude/ and ~/Documents/Personal/AgentMemory."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
VAULT_PATH = Path(os.environ.get('AGENT_MEMORY_VAULT', Path.home() / 'Documents' / 'Personal' / 'AgentMemory'))
CLAUDE_DIR = Path.home() / '.claude'
HOOKS_DEST = CLAUDE_DIR / 'hooks' / 'agent-memory'
SKILL_DEST = CLAUDE_DIR / 'skills' / 'agent-memory'
SETTINGS_PATH = CLAUDE_DIR / 'settings.json'

HOOK_ENTRIES = {
    'SessionStart': [{'hooks': [{'type': 'command', 'command': f'python3 {HOOKS_DEST}/session_start.py'}]}],
    'PostToolUse': [{'matcher': 'Edit|Write', 'hooks': [{'type': 'command', 'command': f'python3 {HOOKS_DEST}/post_tool_use.py'}]}],
    'PreCompact': [{'hooks': [{'type': 'command', 'command': f'python3 {HOOKS_DEST}/pre_compact.py'}]}],
    'SessionEnd': [{'hooks': [{'type': 'command', 'command': f'python3 {HOOKS_DEST}/session_end.py'}]}],
}


def run(cmd, **kwargs):
    print(f'  $ {" ".join(str(c) for c in cmd)}')
    return subprocess.run(cmd, check=True, **kwargs)


def deploy_hooks():
    print('\n[1] Deploying hook scripts...')
    HOOKS_DEST.mkdir(parents=True, exist_ok=True)
    for f in (REPO_ROOT / 'src' / 'hooks').glob('*.py'):
        shutil.copy2(f, HOOKS_DEST / f.name)
        print(f'  copied {f.name}')


def deploy_skill():
    print('\n[2] Deploying skill...')
    SKILL_DEST.mkdir(parents=True, exist_ok=True)
    src = REPO_ROOT / 'src' / 'skills' / 'agent-memory' / 'SKILL.md'
    shutil.copy2(src, SKILL_DEST / 'SKILL.md')
    print('  copied SKILL.md')


def wire_hooks():
    print('\n[3] Wiring hooks into ~/.claude/settings.json...')
    settings = json.loads(SETTINGS_PATH.read_text()) if SETTINGS_PATH.exists() else {}
    hooks = settings.setdefault('hooks', {})
    for event, entries in HOOK_ENTRIES.items():
        if event not in hooks:
            hooks[event] = entries
            print(f'  added {event}')
        else:
            print(f'  skipped {event} (already configured — edit settings.json manually if needed)')
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def bootstrap_vault():
    print('\n[4] Bootstrapping vault...')
    vault_src = REPO_ROOT / 'src' / 'vault'
    for src_file in vault_src.rglob('*'):
        if src_file.is_file():
            rel = src_file.relative_to(vault_src)
            dest = VAULT_PATH / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(src_file, dest)
                print(f'  created {rel}')
            else:
                print(f'  skipped {rel} (already exists)')


def add_to_chezmoi():
    print('\n[5] Adding skill and hooks to chezmoi...')
    files_to_add = [
        SKILL_DEST / 'SKILL.md',
        SETTINGS_PATH,
    ] + list(HOOKS_DEST.glob('*.py'))

    for f in files_to_add:
        try:
            run(['chezmoi', 'add', str(f)])
        except subprocess.CalledProcessError:
            print(f'  chezmoi add failed for {f.name} — add manually if needed')


if __name__ == '__main__':
    print(f'Installing agent-memory')
    print(f'  hooks  → {HOOKS_DEST}')
    print(f'  skill  → {SKILL_DEST}')
    print(f'  vault  → {VAULT_PATH}')

    deploy_hooks()
    deploy_skill()
    wire_hooks()
    bootstrap_vault()
    add_to_chezmoi()

    print('\nDone. Start a new Claude Code session to activate.')
