"""Load a project's mockups configuration (<design>/boards.json) with defaults."""

from pathlib import Path
import json
import subprocess

DEFAULTS = {
    'title': 'Mockups',
    'locale': 'en',
    'wireframes': 'wireframes',
    'frameWidth': 1280,
    'mobile': {'width': 360, 'height': 800},
    'labels': {'script': None, 'allowLatin': []},
    'forbidden': [],
    'playwright': None,
    'generators': [],
    'sections': [],
}


def project_root(start=None):
    start = Path(start or Path.cwd())
    try:
        out = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=start,
                             capture_output=True, text=True, check=True).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


def design_dir(argv):
    """--design <dir> (default: design/ in the git root of the current directory)."""
    if '--design' in argv:
        return Path(argv[argv.index('--design') + 1]).resolve()
    return project_root() / 'design'


def load(design):
    path = design / 'boards.json'
    if not path.exists():
        raise SystemExit(f'mockups: {path} not found; create it as described in the mockups skill')
    data = json.loads(path.read_text())
    config = {**DEFAULTS, **data}
    config['mobile'] = {**DEFAULTS['mobile'], **data.get('mobile', {})}
    config['labels'] = {**DEFAULTS['labels'], **data.get('labels', {})}
    config['design'] = design
    config['wireframesPath'] = design / config['wireframes']
    config['boards'] = [(section['id'], board['id'], board['title'], board['generator'])
                        for section in config['sections'] for board in section.get('boards', [])]
    config['sectionTitles'] = {section['id']: section['title'] for section in config['sections']}
    return config
