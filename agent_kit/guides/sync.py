"""Vendor engineering guides into a project, pinned to official sources.

  agent-kit guides init               create guides.json listing every known guide
  agent-kit guides list               show known guides and the pinned or resolved ref
  agent-kit guides sync [names] [--force]   download and copy guides (unchanged bytes)
  agent-kit guides check              fail when a copy is missing or does not match its pin

guides.json (project root): {"dir": ".agents/vendor", "guides": ["tanstack-query", ...]}.
Guides tied to a package take its version from the project's lockfile
(pnpm-lock.yaml, package-lock.json, yarn.lock or node_modules) and fetch the
matching release tag. Downloads are sparse git fetches; nothing downloaded runs.
"""

from datetime import date
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile

SOURCES = json.loads((Path(__file__).resolve().parent / 'sources.json').read_text())
CONFIG = 'guides.json'


def project_root():
    try:
        out = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def load_config(root):
    path = root / CONFIG
    if not path.exists():
        raise SystemExit(f'guides: {CONFIG} not found; run `agent-kit guides init`')
    config = json.loads(path.read_text())
    unknown = [name for name in config.get('guides', []) if name not in SOURCES]
    if unknown:
        raise SystemExit(f'guides: unknown guides in {CONFIG}: {", ".join(unknown)}')
    return root / config.get('dir', '.agents/vendor'), config.get('guides', [])


def installed_version(root, package):
    """The single installed version of a package, from the lockfile or node_modules."""
    found = set()
    lock = root / 'pnpm-lock.yaml'
    if lock.exists():
        found |= set(re.findall(rf"^\s+'?{re.escape(package)}@(\d[^:'(\s]*)", lock.read_text(), re.M))
    lock = root / 'package-lock.json'
    if lock.exists():
        packages = json.loads(lock.read_text()).get('packages', {})
        found |= {v['version'] for k, v in packages.items() if k.endswith(f'node_modules/{package}') and 'version' in v}
    lock = root / 'yarn.lock'
    if lock.exists():
        for block in lock.read_text().split('\n\n'):
            if re.match(rf'^"?{re.escape(package)}@', block):
                found |= set(re.findall(r'^\s+version:? "?([^"\s]+)', block, re.M))
    if not found:
        manifest = root / 'node_modules' / package / 'package.json'
        if manifest.exists():
            found.add(json.loads(manifest.read_text())['version'])
    if not found:
        raise SystemExit(f'guides: {package} is not installed in this project')
    if len(found) > 1:
        raise SystemExit(f'guides: several versions of {package} are installed ({", ".join(sorted(found))})')
    return found.pop()


def resolve(root, name):
    source = SOURCES[name]
    version = installed_version(root, source['package']) if 'package' in source else None
    return source['ref'].format(version=version), version


def glob_regex(pattern):
    out, i = '', 0
    while i < len(pattern):
        if pattern.startswith('**/', i):
            out, i = out + '(?:.*/)?', i + 3
        elif pattern[i] == '*':
            out, i = out + '[^/]*', i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + '$')


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def fetch(repo, ref, patterns, work):
    """Sparse, shallow, blob-filtered fetch of one ref; returns the commit."""
    git(work, 'init', '-q')
    git(work, 'remote', 'add', 'origin', f'https://github.com/{repo}.git')
    git(work, 'sparse-checkout', 'set', '--no-cone', *[f'/{p}' for p in patterns])
    git(work, 'fetch', '-q', '--depth', '1', '--filter=blob:none', 'origin', ref)
    git(work, 'checkout', '-q', 'FETCH_HEAD')
    return git(work, 'rev-parse', 'HEAD')


def select(work, source):
    include = [glob_regex(p) for p in source['include']]
    exclude = set(source.get('exclude', []))
    files = []
    for path in sorted(work.rglob('*')):
        relative = path.relative_to(work).as_posix()
        if path.is_file() and not relative.startswith('.git/') and relative not in exclude \
                and any(r.match(relative) for r in include):
            files.append(relative)
    return files


def referenced_assets(work, source, files):
    spec = source.get('referencedAssets')
    if not spec:
        return []
    pattern = re.compile(spec['pattern'])
    assets = set()
    for relative in files:
        if relative.endswith('.md'):
            assets |= {f'{spec["root"]}/{m}' for m in pattern.findall((work / relative).read_text())}
    return sorted(assets)


def sync_guide(root, vendor, name, force):
    source = SOURCES[name]
    ref, version = resolve(root, name)
    target = vendor / name
    record = read_source(target)
    if record and record.get('ref') == ref and not force:
        print(f'{name}: up to date ({ref})')
        return
    if target.exists() and not record:
        raise SystemExit(f'guides: {target} exists without SOURCE.md from agent-kit; not overwriting')
    with tempfile.TemporaryDirectory(prefix='agent-kit-guides-') as tmp:
        work = Path(tmp)
        commit = fetch(source['repo'], ref, source['include'], work)
        files = select(work, source)
        assets = referenced_assets(work, source, files)
        if assets:
            git(work, 'sparse-checkout', 'add', *[f'/{a}' for a in assets])
            files += [a for a in assets if (work / a).is_file()]
        if not files:
            raise SystemExit(f'guides: nothing matched for {name} at {ref}')
        if target.exists():
            shutil.rmtree(target)
        copied = []
        for relative in files:
            local = relative.removeprefix(source.get('strip', ''))
            destination = target / local
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(work / relative, destination)
            copied.append((relative, local))
    write_source(target, name, source, ref, commit, version, copied)
    print(f'{name}: {len(copied)} files at {commit[:12]} ({ref})')


def write_source(target, name, source, ref, commit, version, copied):
    lines = [f'# {source["title"]}', '',
             f'- Source: https://github.com/{source["repo"]}/tree/{commit}',
             f'- Ref: `{ref}`',
             f'- Commit: `{commit}`']
    if version:
        lines.append(f'- Version: `{source["package"]}@{version}` (from the project lockfile)')
    lines += [f'- Retrieved: {date.today().isoformat()}',
              f'- License: {source["license"]}',
              f'- Files: {len(copied)}, copied unchanged by `agent-kit guides sync`',
              '', '## Copied files', '']
    lines += [f'- `{upstream}`' + (f' → `{local}`' if local != upstream else '') for upstream, local in copied]
    (target / 'SOURCE.md').write_text('\n'.join(lines) + '\n')


def read_source(target):
    path = target / 'SOURCE.md'
    if not path.exists():
        return None
    text = path.read_text()
    fields = dict(re.findall(r'^- (Ref|Commit): `([^`]+)`', text, re.M))
    listing = text.split('## Copied files', 1)[-1]
    files = [m.group(2) or m.group(1) for m in re.finditer(r'^- `([^`]+)`(?: → `([^`]+)`)?$', listing, re.M)]
    return {'ref': fields.get('Ref'), 'commit': fields.get('Commit'), 'files': files}


def check(root, vendor, names):
    errors = []
    for name in names:
        record = read_source(vendor / name)
        ref, _ = resolve(root, name)
        if not record:
            errors.append(f'{name}: missing; run `agent-kit guides sync {name}`')
        elif record['ref'] != ref:
            errors.append(f'{name}: copy is {record["ref"]}, project needs {ref}; run `agent-kit guides sync {name}`')
        else:
            missing = [f for f in record['files'] if not (vendor / name / f).is_file()]
            if missing:
                errors.append(f'{name}: {len(missing)} copied files are missing (e.g. {missing[0]}); run sync --force')
    if vendor.exists():
        for extra in sorted(p.name for p in vendor.iterdir() if p.is_dir() and p.name not in names):
            errors.append(f'{extra}: not listed in {CONFIG}; remove it or add it to the list')
    print('\n'.join(errors) if errors else f'All {len(names)} guides match their pins.')
    return 1 if errors else 0


def main(argv):
    command = argv[0] if argv else 'help'
    root = project_root()
    if command == 'init':
        path = root / CONFIG
        if not path.exists():
            path.write_text(json.dumps({'dir': '.agents/vendor', 'guides': list(SOURCES)}, indent=2) + '\n')
            print(f'created {CONFIG}; remove the guides this project does not need, then run sync')
        return 0
    if command == 'list':
        for name, source in SOURCES.items():
            print(f'{name:28} {source["title"]}  [{source["ref"]}]')
        return 0
    vendor, configured = load_config(root) if command in ('sync', 'check') else (None, [])
    if command == 'sync':
        names = [a for a in argv[1:] if not a.startswith('--')] or configured
        for name in names:
            if name not in configured:
                raise SystemExit(f'guides: {name} is not listed in {CONFIG}')
            sync_guide(root, vendor, name, '--force' in argv)
        return 0
    if command == 'check':
        return check(root, vendor, configured)
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
