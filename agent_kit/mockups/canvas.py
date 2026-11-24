"""Minimal drawing canvas producing editable Excalidraw elements and matching SVG.

Projects may use it as is or extend it with their own components:

    from canvas import Canvas, scene
    c = Canvas('login-empty')
    c.rect(0, 0, 1280, 960, '#ffffff', '#ffffff', 0)
    c.text(32, 48, 'Вход', 24, weight=600)
"""

from html import escape
import zlib


def _seed(slug, index):
    return zlib.crc32(f'{slug}-{index}'.encode()) & 0x7fffffff


class Canvas:
    def __init__(self, slug):
        self.slug = slug
        self.elements = []
        self.svg = []

    def element(self, kind, x, y, width, height, fill='transparent', stroke='#e4e4e7'):
        index = len(self.elements)
        seed = _seed(self.slug, index)
        item = dict(id=f'{self.slug}-{index}', type=kind, x=x, y=y, width=width, height=height,
                    angle=0, strokeColor=stroke, backgroundColor=fill, fillStyle='solid',
                    strokeWidth=1, strokeStyle='solid', roughness=0, opacity=100,
                    groupIds=[self.slug], frameId=None, roundness=None, seed=seed,
                    version=1, versionNonce=seed, isDeleted=False, boundElements=None,
                    updated=1, link=None, locked=False)
        self.elements.append(item)
        return item

    def rect(self, x, y, w, h, fill='#ffffff', stroke='#e4e4e7', radius=6):
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')
        item = self.element('rectangle', x, y, w, h, fill, stroke)
        if radius:
            item['roundness'] = dict(type=3, value=radius)
        return item

    def circle(self, cx, cy, d, stroke='#71717a', width=1.5, fill='transparent'):
        self.svg.append(f'<circle cx="{cx}" cy="{cy}" r="{d / 2}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        item = self.element('ellipse', cx - d / 2, cy - d / 2, d, d, fill, stroke)
        item['strokeWidth'] = width
        return item

    def text(self, x, y, value, size=14, color='#18181b', weight=400, align='left'):
        """y is the baseline; width is estimated for layout checks."""
        anchor = ' text-anchor="middle"' if align == 'center' else ''
        self.svg.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                        f'fill="{color}"{anchor}>{escape(value)}</text>')
        width = len(value) * size * .58
        left = x - width / 2 if align == 'center' else x
        item = self.element('text', left, y - size, width, size * 1.4, stroke=color)
        item.update(text=value, originalText=value, fontSize=size, fontFamily=2, textAlign=align,
                    verticalAlign='top', baseline=size, containerId=None, lineHeight=1.4, autoResize=True)
        return item

    def line(self, points, color='#71717a', width=1.5):
        coords = ' '.join(f'{x},{y}' for x, y in points)
        self.svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" '
                        'stroke-linecap="round" stroke-linejoin="round"/>')
        x, y = min(p[0] for p in points), min(p[1] for p in points)
        w, h = max(p[0] for p in points) - x, max(p[1] for p in points) - y
        item = self.element('line', x, y, w, h, stroke=color)
        item.update(points=[[px - x, py - y] for px, py in points], strokeWidth=width,
                    lastCommittedPoint=None, startBinding=None, endBinding=None,
                    startArrowhead=None, endArrowhead=None)
        return item

    def body(self):
        return '<g font-family="Arial, Helvetica, sans-serif">' + ''.join(self.svg) + '</g>'

    def write_svg(self, path):
        width, height = getattr(self, 'viewport', (1280, 960))
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
                        f'viewBox="0 0 {width} {height}">' + self.body() + '</svg>\n')


def scene(elements, zoom=.7):
    return dict(type='excalidraw', version=2, source='https://excalidraw.com', elements=elements,
                appState=dict(gridSize=None, viewBackgroundColor='#f4f4f5', scrollX=64, scrollY=64,
                              zoom=dict(value=zoom)), files={})
