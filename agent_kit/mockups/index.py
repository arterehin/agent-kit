"""Write <design>/index.html: a browsable table of contents of all boards.

Usage: python3 index.py [--design <dir>]
The page is built from the boards themselves and never edited by hand.
"""

from html import escape
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as configuration  # noqa: E402

STRINGS = {
    'en': dict(search='Search screens', whole='Whole board (PNG)', edit='edit', generator='generator', frames='frames',
               lead='Built from the boards by the mockups build. Click a frame to open it in full.'),
    'ru': dict(search='Поиск по экранам', whole='Вся доска (PNG)', edit='правка', generator='генератор', frames='кадры',
               lead='Страница собирается из досок сборкой макетов. Нажмите на кадр, чтобы открыть его целиком.'),
}


def board_outline(folder, board):
    """Groups and frames in layout order: board.json for screen boards, the scene for catalogs."""
    manifest = folder / 'board.json'
    if manifest.exists():
        groups = json.loads(manifest.read_text())['groups']
        return [dict(number=g['number'], title=g['title'], flow=g['flow'],
                     frames=[dict(slug=f['state'], code=f['code'], title=f['title'], subtitle=f['subtitle'])
                             for f in g['frames']]) for g in groups]
    elements = json.loads((folder / f'{board}.excalidraw').read_text())['elements']
    groups = sorted((e for e in elements if e.get('customData', {}).get('component') == 'DesignBoardGroup'),
                    key=lambda e: e['y'])
    return [dict(number=f'{n:02d}', title=g['customData']['name'], flow=False, frames=[])
            for n, g in enumerate(groups, 1)]


def frame_card(path, frame):
    image = f'{path}/states/{frame["slug"]}.png'
    search = escape(f'{frame["code"]} {frame["title"]} {frame["subtitle"]}'.lower())
    return (f'<a class="frame" href="{image}" target="_blank" data-search="{search}">'
            f'<img src="{image}" loading="lazy" alt="">'
            f'<span class="code">{escape(frame["code"])}</span> <b>{escape(frame["title"])}</b>'
            f'<small>{escape(frame["subtitle"])}</small></a>')


def render(config):
    text = STRINGS.get(config['locale'], STRINGS['en'])
    design = config['design'].name
    nav, body = [], []
    for section, section_title in config['sectionTitles'].items():
        boards = [b for b in config['boards'] if b[0] == section]
        nav.append(f'<li><span>{escape(section_title)}</span><ul>')
        for _, board, title, generator in boards:
            anchor = f'{section}-{board}'
            path = f'{config["wireframes"]}/{section}/{board}'
            outline = board_outline(config['wireframesPath'] / section / board, board)
            catalog = not any(group['frames'] for group in outline)
            nav.append(f'<li><a href="#{anchor}">{escape(title)}</a></li>')
            body.append(f'<section class="board" id="{anchor}" data-search="{escape(title.lower())}">'
                        f'<h2>{escape(section_title)} / {escape(title)}</h2>'
                        + (f'<p class="meta"><a href="{path}/{board}.png" target="_blank">{text["whole"]}</a>'
                           f' · {text["edit"]}: <code>{design}/{path}/{board}.excalidraw</code>' if catalog else
                           f'<p class="meta">{text["frames"]}: <code>{design}/{path}/states/</code>')
                        + f' · {text["generator"]}: <code>{design}/{generator}</code></p>')
            for group in outline:
                body.append(f'<div class="group{" flow" if group["flow"] else ""}" data-search="{escape(group["title"].lower())}">'
                            f'<h3>{group["number"]} · {escape(group["title"])}</h3>')
                if group['frames']:
                    body.append('<div class="frames">' + ''.join(frame_card(path, f) for f in group['frames']) + '</div>')
                body.append('</div>')
            if catalog:
                body.append(f'<a class="whole" href="{path}/{board}.png" target="_blank">'
                            f'<img src="{path}/{board}.png" loading="lazy" alt=""></a>')
            body.append('</section>')
        nav.append('</ul></li>')
    page = PAGE
    for key, value in {'lang': config['locale'], 'title': escape(config['title']), 'search': text['search'],
                       'lead': text['lead'], 'nav': ''.join(nav), 'body': ''.join(body)}.items():
        page = page.replace('{' + key + '}', value)
    return page


def main(argv):
    config = configuration.load(configuration.design_dir(argv))
    (config['design'] / 'index.html').write_text(render(config))
    print(f'index.html: {len(config["boards"])} boards.')


PAGE = '''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root { color-scheme: light; font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; color: #18181b; }
  body { margin: 0; display: grid; grid-template-columns: 260px 1fr; min-height: 100vh; }
  nav { position: sticky; top: 0; height: 100vh; overflow: auto; border-right: 1px solid #e4e4e7; background: #fafafa; padding: 16px; box-sizing: border-box; }
  nav input { width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #e4e4e7; border-radius: 6px; font: inherit; margin-bottom: 16px; }
  nav ul { list-style: none; margin: 0; padding: 0; }
  nav > ul > li { margin-bottom: 12px; }
  nav > ul > li > span { font-weight: 600; }
  nav ul ul { padding-left: 12px; margin-top: 4px; }
  nav a { color: #3f3f46; text-decoration: none; display: block; padding: 2px 0; }
  nav a:hover { color: #18181b; text-decoration: underline; }
  main { padding: 24px 32px 64px; min-width: 0; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .lead { color: #71717a; margin: 0 0 24px; }
  .board { margin-bottom: 48px; }
  h2 { font-size: 20px; margin: 0 0 4px; }
  .meta { color: #71717a; margin: 0 0 16px; }
  .meta code { font-size: 12px; }
  h3 { font-size: 15px; margin: 16px 0 8px; }
  .frames { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
  .frame { position: relative; display: block; color: inherit; text-decoration: none; border: 1px solid #e4e4e7; border-radius: 8px; padding: 8px; background: #fff; }
  .frame:hover { border-color: #a1a1aa; }
  .frame img, .whole img { width: 100%; display: block; border-radius: 4px; background: #f4f4f5; margin-bottom: 6px; }
  .whole img { max-width: 960px; border: 1px solid #e4e4e7; }
  .code { color: #71717a; font-variant-numeric: tabular-nums; }
  .frame small { display: block; color: #71717a; margin-top: 2px; }
  .flow .frame:not(:last-child)::after { content: '→'; position: absolute; right: -14px; top: 30%; color: #71717a; font-size: 16px; }
  [hidden] { display: none !important; }
</style>
</head>
<body>
<nav><input type="search" id="search" placeholder="{search}" aria-label="{search}"><ul>{nav}</ul></nav>
<main>
<h1>{title}</h1>
<p class="lead">{lead}</p>
{body}
</main>
<script>
  const input = document.getElementById('search');
  input.addEventListener('input', () => {
    const query = input.value.trim().toLowerCase();
    document.querySelectorAll('.board').forEach(board => {
      const boardMatch = !query || board.dataset.search.includes(query);
      let boardVisible = boardMatch;
      board.querySelectorAll('.group').forEach(group => {
        const groupMatch = boardMatch || group.dataset.search.includes(query);
        let groupVisible = groupMatch;
        group.querySelectorAll('.frame').forEach(frame => {
          const visible = groupMatch || frame.dataset.search.includes(query);
          frame.hidden = !visible;
          groupVisible = groupVisible || visible;
        });
        group.hidden = !groupVisible;
        boardVisible = boardVisible || groupVisible;
      });
      board.hidden = !boardVisible;
    });
  });
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main(sys.argv)
