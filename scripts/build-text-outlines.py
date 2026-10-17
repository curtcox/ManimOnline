#!/usr/bin/env python3
"""Build src/text-outlines.json from Liberation Sans 2.1.5 and DejaVu Sans Mono 2.35.

Usage: build-text-outlines.py LIBERATION_DIR DEJAVU_DIR CM_TYPE1_DIR [OUTPUT]

CM_TYPE1_DIR holds the AMS Computer Modern Type 1 fonts (cmr10/cmmi10/cmsy10.pfb, e.g.
texmf-dist/fonts/type1/public/amsfonts/cm): Community's DecimalNumber typesets each
character as MathTex, which dvisvgm writes as their outlines in big points.

Community's Text draws Pango/Cairo glyph outlines; on Linux the default sans font is
Liberation Sans and the monospace font (Code) is DejaVu Sans Mono. The preview
reproduces those outlines from the fonts' TrueType contours (font units, on/off-curve
flags), advances and HarfBuzz kerning, for the characters the runtime has layout
metrics for. Requires fontTools and uharfbuzz. The output is derived from fonts under
the SIL Open Font License 1.1 and the Bitstream Vera license; keep
src/text-outlines-LICENSE.txt next to it.
"""
import ast
import json
import os
import re
import sys
import unicodedata

from fontTools.pens.recordingPen import RecordingPen
from fontTools.t1Lib import T1Font
from fontTools.ttLib import TTFont
import uharfbuzz as hb

# Face keys: r(egular), b(old), i(talic), x (bold italic), prefixed by family: none for
# Liberation Sans, m for DejaVu Sans Mono.
FAMILIES = (('', 0, 'LiberationSans-{}.ttf', {'r': 'Regular', 'b': 'Bold', 'i': 'Italic', 'x': 'BoldItalic'}),
            ('m', 1, 'DejaVuSansMono{}.ttf', {'r': '', 'b': '-Bold', 'i': '-Oblique', 'x': '-BoldOblique'}))
TABLES = ('_SANS_GLYPHS', '_SANS_BOLD_GLYPHS', '_SANS_ITALIC_GLYPHS', '_SANS_BOLD_ITALIC_GLYPHS', '_MONO_GLYPHS')
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


# DecimalNumber characters: digits and + from cmr10, . and , from cmmi10, the minus
# from cmsy10 (math mode). \\dots is three cmmi10 periods 4.427808 bp apart.
TEX_GLYPHS = (('cmr10', {**{str(i): name for i, name in enumerate(
                  'zero one two three four five six seven eight nine'.split())}, '+': 'plus'}),
              ('cmmi10', {'.': 'period', ',': 'comma'}), ('cmsy10', {'-': 'minus'}))
DOTS_STEP = 4.427808


def tex_glyphs(directory):
    """Outline commands in dvisvgm's coordinates: big points (10 pt fonts), y down, printed
    with six decimals."""
    scale = 72 / 72.27 / 100
    def bp(value):
        return float('%.6f' % (value * scale))
    glyphs = {}
    for font, chars in TEX_GLYPHS:
        t1 = T1Font(os.path.join(directory, font + '.pfb'))
        t1.parse()
        glyph_set = t1.getGlyphSet()
        for char, name in chars.items():
            pen = RecordingPen()
            glyph_set[name].draw(pen)
            glyphs[char] = [[{'moveTo': 'M', 'lineTo': 'L', 'curveTo': 'C', 'closePath': 'Z'}[op]] + [bp(v) * (1 if k % 2 == 0 else -1)
                                              for point in args for k, v in enumerate(point)]
                            for op, args in pen.value]
    glyphs['\u2026'] = [[op[0]] + [v + DOTS_STEP * n if k % 2 == 0 else v for k, v in enumerate(op[1:])]
                         for n in range(3) for op in glyphs['.']]
    return glyphs


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    directories = sys.argv[1:3]
    output = sys.argv[4] if len(sys.argv) > 4 else os.path.join(ROOT, 'src', 'text-outlines.json')
    chars = characters()
    data = {'source': 'Liberation Sans 2.1.5 and AMS Computer Modern 3.002 (SIL Open Font License 1.1), '
                      'DejaVu Sans Mono 2.35 (Bitstream Vera license); see text-outlines-LICENSE.txt',
            'faces': {prefix + key: face_data(os.path.join(directories[where], pattern.format(name)), chars)
                      for prefix, where, pattern, faces in FAMILIES for key, name in faces.items()},
            'tex': tex_glyphs(sys.argv[3])}
    with open(output, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
        handle.write('\n')
    print(output, os.path.getsize(output), 'bytes')


if __name__ == '__main__':
    main()
