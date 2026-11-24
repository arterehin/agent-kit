"""Write wireframe boards: numbered scenario groups of equal frames.

A screen board lives in its own folder: board.json (groups, frame codes, titles,
subtitles, flows) and states/ with one .excalidraw/.svg per frame. Frame codes
come from the layout (group.position), so they never go stale.

A frame canvas (canvas.Canvas or the project's own) must provide .elements
(Excalidraw elements), a writable .viewport (width, height) and .write_svg(path)
that writes a standalone SVG of that size; scene(elements) returns an Excalidraw
scene dict.
"""

import json


def preserve_unchanged_updates(path, data):
    """Keep edit timestamps of identical elements so regeneration is idempotent."""
    if path.exists():
        old = {item['id']: item for item in json.loads(path.read_text())['elements']}
        for item in data['elements']:
            previous = old.get(item['id'])
            if previous and json.dumps(
                    {k: v for k, v in item.items() if k != 'updated'}, sort_keys=True) == json.dumps(
                    {k: v for k, v in previous.items() if k != 'updated'}, sort_keys=True):
                item['updated'] = previous['updated']
    return data


def write_scene(path, data):
    """Write an Excalidraw scene, keeping timestamps of unchanged elements."""
    preserve_unchanged_updates(path, data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def frame_code(row, column):
    return f'{row + 1}.{column + 1}'


def write_board(scene, variants, groups, output, flows=(), frame_width=1280, frame_height=960):
    """Write a board: states/<state>.excalidraw|svg per frame and board.json.

    variants: (state, 'Title · subtitle', canvas); groups: (title, states);
    flows: group titles whose frames are sequential steps (shown with arrows).
    board.json keeps the board structure: groups, frame codes, titles, subtitles.
    """
    by_state = {state: (label, canvas) for state, label, canvas in variants}
    states_in_groups = [state for _, keys in groups for state in keys]
    assert len(states_in_groups) == len(set(states_in_groups)) and set(states_in_groups) == set(by_state), \
        'groups must list every variant once'
    assert set(flows) <= {title for title, _ in groups}, 'flows must name existing groups'
    states = output / 'states'
    states.mkdir(parents=True, exist_ok=True)
    manifest = {'frameWidth': frame_width, 'frameHeight': frame_height, 'groups': []}
    for row, (group_title, keys) in enumerate(groups):
        frames = []
        for column, state in enumerate(keys):
            label, canvas = by_state[state]
            title, _, subtitle = label.partition(' · ')
            canvas.viewport = (frame_width, frame_height)
            canvas.write_svg(states / f'{state}.svg')
            write_scene(states / f'{state}.excalidraw', scene(canvas.elements))
            frames.append({'state': state, 'code': frame_code(row, column), 'title': title, 'subtitle': subtitle})
        manifest['groups'].append({'number': f'{row + 1:02d}', 'title': group_title,
                                   'flow': group_title in flows, 'frames': frames})
    for stale in states.iterdir():
        if stale.stem not in by_state:
            stale.unlink()
    for leftover in output.iterdir():
        if leftover.is_file() and leftover.name != 'board.json':
            leftover.unlink()
    (output / 'board.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'{output.name}: {len(variants)} frames in {len(groups)} groups.')
