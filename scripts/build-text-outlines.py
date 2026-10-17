#!/usr/bin/env python3
"""Build src/text-outlines.json from the Liberation Sans 2.1.5 TrueType fonts.

Usage: build-text-outlines.py FONT_DIR [OUTPUT]

Community's Text draws Pango/Cairo glyph outlines; on Linux the default sans font is
Liberation Sans. The preview reproduces those outlines from the font's TrueType
contours (font units, on/off-curve flags), advances and HarfBuzz kerning, for the
characters the runtime has layout metrics for. Requires fontTools and uharfbuzz.
The output is derived from fonts under the SIL Open Font License 1.1; keep
src/text-outlines-LICENSE.txt next to it.
"""
import ast
import json
import os
import re
import sys
import unicodedata

from fontTools.ttLib import TTFont
import uharfbuzz as hb

FACES = {'r': 'Regular', 'b': 'Bold', 'i': 'Italic', 'x': 'BoldItalic'}
TABLES = ('_SANS_GLYPHS', '_SANS_BOLD_GLYPHS', '_SANS_ITALIC_GLYPHS', '_SANS_BOLD_ITALIC_GLYPHS')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def characters():
    source = open(os.path.join(ROOT, 'src', 'manim-lite.py'), encoding='utf-8').read()
    chars = set()
    for name in TABLES:
        match = re.search(r'^' + name + r' = (\{.*\})$', source, re.M)
        chars.update(ast.literal_eval(match.group(1)))
    return sorted(chars)


def script(char):
    name = unicodedata.name(char, '')
    if name.startswith('GREEK'):
        return 'grek'
    if name.startswith('LATIN') or char.isalpha():
        return 'latn'
    return None  # Common: Pango itemizes it with its neighbour.


def face_data(path, chars):
    font = TTFont(path)
    cmap, glyf, hmtx = font.getBestCmap(), font['glyf'], font['hmtx']
    glyphs = {}
    for char in chars:
        name = cmap.get(ord(char))
        if name is None:
            continue
        coordinates, ends, flags = glyf[name].getCoordinates(glyf)
        contours, start = [], 0
        for end in ends:
            points = range(start, end + 1)
            contours.append([''.join('1' if flags[i] & 1 else '0' for i in points)] +
                            [int(v) for i in points for v in coordinates[i]])
            start = end + 1
        glyphs[char] = [hmtx[name][0], contours]
    # HarfBuzz and Pango hide a soft hyphen inside a line: no advance and no outline.
    if '\xad' in glyphs:
        glyphs['\xad'] = [0, []]
    blob = open(path, 'rb').read()
    face = hb.Face(blob)
    hbfont = hb.Font(face)
    upem = face.upem
    hbfont.scale = (upem, upem)
    kerning = {}
    present = [c for c in chars if c in glyphs and c != '\xad']
    for a in present:
        for b in present:
            scripts = {script(a), script(b)} - {None}
            if len(scripts) > 1:
                continue  # Pango shapes different scripts in separate runs.
            buffer = hb.Buffer()
            buffer.add_str(a + b)
            buffer.direction = 'ltr'
            buffer.script = scripts.pop() if scripts else 'latn'
            buffer.language = 'en'
            hb.shape(hbfont, buffer, {'kern': True, 'liga': True})
            infos, positions = buffer.glyph_infos, buffer.glyph_positions
            if len(infos) != 2:
                raise SystemExit(f'{a + b!r} does not shape to two glyphs')
            delta = positions[0].x_advance - glyphs[a][0]
            if delta:
                kerning[a + b] = delta
    # Pango's line height for MarkupText: HarfBuzz's scaled hhea ascender plus descender.
    return {'upem': upem, 'ascent': font['hhea'].ascent, 'descent': -font['hhea'].descent,
            'glyphs': glyphs, 'kerning': kerning}


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    directory = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'src', 'text-outlines.json')
    chars = characters()
    data = {'source': 'Liberation Sans 2.1.5 (SIL Open Font License 1.1; see text-outlines-LICENSE.txt)',
            'faces': {key: face_data(os.path.join(directory, f'LiberationSans-{name}.ttf'), chars)
                      for key, name in FACES.items()}}
    with open(output, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        handle.write('\n')
    print(output, os.path.getsize(output), 'bytes')


if __name__ == '__main__':
    main()
