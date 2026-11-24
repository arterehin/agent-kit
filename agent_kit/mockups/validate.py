"""Check that every wireframe board follows the mockups conventions.

Usage: python3 validate.py [--design <dir>]
Exit code 1 and a list of violations when anything is off.

A screen board folder holds board.json and states/ (one .excalidraw/.svg/.png
per frame). A catalog in patterns/ holds <board>.excalidraw/.svg/.png.
"""

from pathlib import Path
import json
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as configuration  # noqa: E402
import index  # noqa: E402

SECTION = re.compile(r'^\d\d-[a-z][a-z0-9-]*$')
NAME = re.compile(r'^[a-z][a-z0-9-]*$')
GROUP_TITLE = re.compile(r'^(\d\d) · (\S.*)$')
FRAME_TITLE = re.compile(r'^(\d+)\.(\d+) · (\S.*)$')
TITLE_SIZE, SUBTITLE_SIZE, CHAR_WIDTH = 20, 12, .58
# Process and history vocabulary never belongs on a board.
FORBIDDEN = [
    (r'\b(accepted|approved|owner|superseded|deprecated|historical|deferred|proposal|proposed|todo|step \d)\b', 'process wording', re.I),
    (r'(принят|утвержд|отложен|согласован|устарел|\bшаг \d|будущ\w* шаг)', 'process wording', re.I),
    (r'\bNEW\b', 'process marker', 0),
    (r'\b20\d\d-\d\d-\d\d\b', 'process date', 0),
    (r'(openspec|docs/|\.md\b|\.py\b|\.excalidraw\b)', 'file or document reference', re.I),
    (r'(?<![\w/])[A-Z]{1,3}\d{0,2}(?:/[A-Z]{1,3}\d{0,2})+(?![\w/])', 'frame code of another board', 0),
]


def png_size(path):
    with path.open('rb') as handle:
        return struct.unpack('>II', handle.read(24)[16:24])


def svg_size(path):
    match = re.search(r'<svg[^>]*width="(\d+)" height="(\d+)"', path.read_text())
    return int(match.group(1)), int(match.group(2))


class Validator:
    def __init__(self, config):
        self.config = config
        self.errors = []
        self.root = config['design'].parent
        self.forbidden = [(re.compile(p, f), reason) for p, reason, f in FORBIDDEN]
        self.forbidden += [(re.compile(p), 'project-forbidden wording') for p in config['forbidden']]
        self.allow = set(config['labels']['allowLatin'])
        self.mobile = (config['mobile']['width'], config['mobile']['height'])

    def add(self, path, message):
        try:
            shown = path.relative_to(self.root)
        except ValueError:
            shown = path
        self.errors.append(f'{shown}: {message}')

    def check_text(self, path, text):
        for pattern, reason in self.forbidden:
            if pattern.search(text):
                self.add(path, f'{reason}: {text!r}')

    def check_label(self, path, text, size):
        self.check_text(path, text)
        if '\n' in text:
            self.add(path, f'label must be one line: {text!r}')
        if len(text) * size * CHAR_WIDTH > self.config['frameWidth']:
            self.add(path, f'label wider than a frame: {text!r}')
        if self.config['labels']['script'] == 'cyrillic':
            words = re.findall(r'[^\s·;,:()«»"“”]+', text)
            foreign = [w for w in words if re.search(r'[A-Za-z]', w) and not w.startswith('/')
                       and w.strip('.') not in self.allow and not re.fullmatch(r'[\d×.]+', w)]
            if foreign:
                self.add(path, f'label must be in the board language (found {", ".join(foreign)}): {text!r}')

    def check_exports(self, stem):
        for extension in ('excalidraw', 'svg', 'png'):
            if not stem.with_suffix('.' + extension).exists():
                self.add(stem, f'missing .{extension}')
        svg, png = stem.with_suffix('.svg'), stem.with_suffix('.png')
        if svg.exists() and png.exists() and png_size(png) != svg_size(svg):
            self.add(png, 'PNG is out of date with its SVG (size differs); run the build')

    def mobile_sizes(self, elements):
        """Phone viewports drawn in a frame, however the generator marks them."""
        sizes = set()
        for item in elements:
            data = item.get('customData', {})
            if data.get('component') == 'DesignReviewViewport':
                sizes.add((data.get('width'), data.get('height')))
            for key in ('viewport', 'mobileViewport'):
                value = data.get(key)
                if isinstance(value, list) and len(value) == 2 and value[0] < self.config['frameWidth']:
                    sizes.add(tuple(value))
        return sizes

    def check_screen_board(self, board):
        manifest_path = board / 'board.json'
        manifest = json.loads(manifest_path.read_text())
        frame_size = (manifest.get('frameWidth'), manifest.get('frameHeight'))
        if frame_size[0] != self.config['frameWidth']:
            self.add(manifest_path, f'frames must be {self.config["frameWidth"]} px wide: {frame_size}')
        states = board / 'states'
        expected, seen = set(), set()
        size_label = f'{self.mobile[0]} px'
        for row, group in enumerate(manifest['groups'], 1):
            if group.get('number') != f'{row:02d}':
                self.add(manifest_path, f'group {group.get("title")!r} must be numbered {row:02d}')
            self.check_label(manifest_path, group['title'], 28)
            if not group['frames']:
                self.add(manifest_path, f'group {group["title"]!r} has no frames')
            for column, frame in enumerate(group['frames'], 1):
                state = frame['state']
                if frame.get('code') != f'{row}.{column}':
                    self.add(manifest_path, f'frame {state} must have code {row}.{column}')
                if not NAME.match(state):
                    self.add(manifest_path, f'state name must be lower-case kebab-case: {state}')
                if state in seen:
                    self.add(manifest_path, f'duplicate state: {state}')
                seen.add(state)
                self.check_label(manifest_path, f'{row}.{column} · {frame["title"]}', TITLE_SIZE)
                subtitle = frame.get('subtitle', '')
                if subtitle:
                    self.check_label(manifest_path, subtitle, SUBTITLE_SIZE)
                    first = re.split(r'[\s;,]', subtitle, maxsplit=1)[0]
                    if subtitle[:1].isupper() and subtitle[1:2].islower() and first not in self.allow:
                        self.add(manifest_path, f'subtitle must start with a lower-case letter: {subtitle!r}')
                expected |= {f'{state}.{extension}' for extension in ('excalidraw', 'svg', 'png')}
                self.check_exports(states / state)
                svg = states / f'{state}.svg'
                if svg.exists() and svg_size(svg) != frame_size:
                    self.add(svg, f'frame must be {frame_size[0]}×{frame_size[1]}: {svg_size(svg)}')
                scene = states / f'{state}.excalidraw'
                if not scene.exists():
                    continue
                elements = json.loads(scene.read_text())['elements']
                for element in elements:
                    if element['type'] == 'text' and element.get('text'):
                        self.check_text(scene, element['text'])
                mobile = self.mobile_sizes(elements)
                if mobile - {self.mobile}:
                    self.add(scene, f'mobile viewport must be {self.mobile[0]}×{self.mobile[1]}: {sorted(mobile)}')
                label = f'{group["title"]} {frame["title"]} {subtitle}'
                if bool(mobile) != (size_label in label):
                    self.add(scene, f'only mobile frames say "{size_label}" in their label or group: {label!r}')
        if states.is_dir():
            for item in states.iterdir():
                if item.name not in expected and not item.name.startswith('.'):
                    self.add(item, 'file is not a frame of this board')
        else:
            self.add(board, 'missing states/ folder')

    def check_catalog(self, board):
        self.check_exports(board / board.name)
        scene = board / f'{board.name}.excalidraw'
        if not scene.exists():
            return
        texts = [e for e in json.loads(scene.read_text())['elements'] if e['type'] == 'text' and e.get('text')]
        for element in texts:
            self.check_text(scene, element['text'])
        numbers = [int(GROUP_TITLE.match(e['text']).group(1))
                   for e in sorted(texts, key=lambda e: e['y']) if GROUP_TITLE.match(e['text'])]
        if numbers != list(range(1, len(numbers) + 1)):
            self.add(scene, f'group numbers must run 01..{len(numbers):02d} without gaps: {numbers}')
        by_group = {}
        for element in texts:
            match = FRAME_TITLE.match(element['text'])
            if match:
                by_group.setdefault(int(match.group(1)), []).append((element['y'], element['x'], int(match.group(2))))
                self.check_label(scene, element['text'], TITLE_SIZE)
        for group, items in sorted(by_group.items()):
            positions = [p for _, _, p in sorted(items)]
            if group not in numbers or positions != list(range(1, len(positions) + 1)):
                self.add(scene, f'item codes in group {group:02d} must run {group}.1..{group}.{len(positions)} in reading order')

    def run(self):
        wireframes = self.config['wireframesPath']
        for section in sorted(p for p in wireframes.iterdir() if not p.name.startswith('.')):
            if not section.is_dir() or not (SECTION.match(section.name) or section.name == 'patterns'):
                self.add(section, 'top level holds only NN-section folders and patterns/')
                continue
            for board in sorted(p for p in section.iterdir() if not p.name.startswith('.')):
                if not board.is_dir() or not NAME.match(board.name):
                    self.add(board, 'a section holds only board folders named in kebab-case')
                    continue
                screen = (board / 'board.json').exists()
                if not screen and section.name != 'patterns':
                    self.add(board, 'a screen board needs board.json and states/ (write it with boardkit.write_board)')
                    continue
                allowed = {'board.json', 'states'} if screen else {f'{board.name}.{e}' for e in ('excalidraw', 'svg', 'png')}
                for item in board.iterdir():
                    if item.name not in allowed and not item.name.startswith('.'):
                        self.add(item, 'unexpected file in a board folder')
                if screen:
                    self.check_screen_board(board)
                else:
                    self.check_catalog(board)
        on_disk = {(b.parent.name, b.name) for b in wireframes.glob('*/*') if b.is_dir()}
        registered = {(section, board) for section, board, _, _ in self.config['boards']}
        for section, board in sorted(on_disk - registered):
            self.add(wireframes / section / board, 'board is missing from boards.json')
        for section, board in sorted(registered - on_disk):
            self.add(wireframes / section, f'registered board {board} does not exist')
        for _, _, _, generator in self.config['boards']:
            if not (self.config['design'] / generator).exists():
                self.add(self.config['design'] / generator, 'generator listed in boards.json does not exist')
        page = self.config['design'] / 'index.html'
        if not page.exists() or page.read_text() != index.render(self.config):
            self.add(page, 'table of contents is out of date; run the build')
        return self.errors


def main(argv):
    config = configuration.load(configuration.design_dir(argv))
    errors = Validator(config).run()
    if errors:
        print('\n'.join(errors))
        print(f'\n{len(errors)} violation(s).')
        return 1
    print('All boards follow the conventions.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
