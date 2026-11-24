"""Install agent-kit skills into a project so every agent reads the same rules.

Skills are copied to .agents/skills/<name>/ (read by Codex and other agents) and
linked from .claude/skills/<name> for Claude Code. Re-running refreshes them.
"""

from pathlib import Path
import json
import shutil
import subprocess

PACKAGE = Path(__file__).resolve().parent
SKILLS = PACKAGE / 'skills'
MARKER = '.agent-kit'


def project_root():
    try:
        out = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def install_skill(root, name):
    target = root / '.agents' / 'skills' / name
    if target.exists() and not (target / MARKER).exists():
        raise SystemExit(f'agent-kit: {target} exists and was not installed by agent-kit; not overwriting')
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SKILLS / name, target)
    (target / MARKER).write_text('Installed by agent-kit; refresh with `agent-kit skills sync`.\n')
    link = root / '.claude' / 'skills' / name
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        if not link.is_symlink():
            raise SystemExit(f'agent-kit: {link} exists and is not a link; not overwriting')
        link.unlink()
    link.symlink_to(Path('..', '..', '.agents', 'skills', name))
    print(f'skill {name}: .agents/skills/{name} (+ .claude/skills/{name})')


def skills_sync():
    root = project_root()
    installed = [p.name for p in (root / '.agents' / 'skills').glob('*') if (p / MARKER).exists()]
    for name in installed:
        install_skill(root, name)
    if not installed:
        print('No agent-kit skills installed in this project.')
    return 0


BOARDS_TEMPLATE = {
    'title': 'Mockups',
    'locale': 'en',
    'frameWidth': 1280,
    'mobile': {'width': 360, 'height': 800},
    'labels': {'script': None, 'allowLatin': []},
    'playwright': 'package.json',
    'generators': [],
    'sections': [],
}


def mockups_init(argv):
    root = project_root()
    design = Path(argv[argv.index('--design') + 1]).resolve() if '--design' in argv else root / 'design'
    (design / 'scripts').mkdir(parents=True, exist_ok=True)
    (design / 'wireframes').mkdir(parents=True, exist_ok=True)
    config = design / 'boards.json'
    if not config.exists():
        config.write_text(json.dumps(BOARDS_TEMPLATE, indent=2) + '\n')
        print(f'created {config.relative_to(root)}')
    install_skill(root, 'mockups')
    return 0
