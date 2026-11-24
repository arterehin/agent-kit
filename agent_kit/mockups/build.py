"""Rebuild every board, render changed PNGs, write the index, validate.

Usage:
  python3 build.py [--design <dir>]          regenerate, render, index, validate
  python3 build.py [--design <dir>] --check  same, and fail if a board was out of date

Generators run in boards.json order with this folder on PYTHONPATH, so they can
`import boardkit`. PNG rendering needs Node and Playwright (see render-png.mjs).
"""

from pathlib import Path
import json
import os
import subprocess
import sys

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
import config as configuration  # noqa: E402
import index  # noqa: E402
import validate  # noqa: E402

IGNORED = {'updated', 'version', 'versionNonce', 'seed'}


def normalized(path):
    """Content that matters: Excalidraw without edit bookkeeping, SVG as text."""
    if path.suffix == '.json':
        return path.read_text()
    if path.suffix == '.excalidraw':
        def strip(value):
            if isinstance(value, dict):
                return {k: strip(v) for k, v in value.items() if k not in IGNORED}
            if isinstance(value, list):
                return [strip(v) for v in value]
            return value
        return json.dumps(strip(json.loads(path.read_text())), sort_keys=True)
    return path.read_text()


def snapshot(wireframes):
    return {path: normalized(path) for path in wireframes.rglob('*') if path.suffix in ('.excalidraw', '.svg', '.json')}


def run(command, root, env=None):
    shown = command if len(command) <= 4 else [*command[:2], f'... {len(command) - 2} files']
    print('$', ' '.join(str(part) for part in shown), flush=True)
    subprocess.run(command, cwd=root, check=True, env=env)


def main(argv):
    config = configuration.load(configuration.design_dir(argv))
    design, wireframes = config['design'], config['wireframesPath']
    root = configuration.project_root(design)
    wireframes.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(filter(None, [str(KIT), os.environ.get('PYTHONPATH')]))}
    before = snapshot(wireframes)
    for generator in config['generators']:
        run([sys.executable, design / generator], root, env)
    after = snapshot(wireframes)
    changed = sorted(path for path in after if before.get(path) != after[path])
    removed = sorted(set(before) - set(after))
    for png in wireframes.rglob('*.png'):
        if not png.with_suffix('.svg').exists():
            png.unlink()
    svgs = [path for path in sorted(wireframes.rglob('*.svg'))
            if path in changed or not path.with_suffix('.png').exists()]
    if svgs:
        playwright = [] if not config['playwright'] else ['--from', str(root / config['playwright'])]
        run(['node', KIT / 'render-png.mjs', *playwright, *svgs], root)
    (design / 'index.html').write_text(index.render(config))
    print(f'index.html: {len(config["boards"])} boards.')
    if '--check' in argv and (changed or removed):
        print('\nBoards were out of date with their generators:')
        for path in changed + removed:
            print('  ', path.relative_to(root))
        return 1
    errors = validate.Validator(config).run()
    if errors:
        print('\n'.join(errors))
        print(f'\n{len(errors)} violation(s).')
        return 1
    print('All boards follow the conventions.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
