"""Write one SVG QR code per snippet for use in the production Manim scenes.

Usage: python3 video-series/tools/make_qr_svgs.py [output-dir]

Requires the `segno` package (pip install segno). Reads qr-links.json, so run
tools/qr-links.mjs first. Codes use error correction level M and a 4-module quiet
zone with black modules on white, which phone cameras read most reliably from video.
It also writes production/qr-matrices.json (committed; rows of "0"/"1" per code, without the quiet
zone), which production/common.py draws as native vector squares: Manim's SVG import
does not keep segno's stroked module paths, so do not load the SVGs into Manim.
"""
import json
import sys
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]

try:
    import segno
except ImportError:
    sys.exit('This script needs segno: pip install segno')


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else SERIES / 'build' / 'qr'
    out.mkdir(parents=True, exist_ok=True)
    rows = json.loads((SERIES / 'qr-links.json').read_text())
    matrices = {}
    for row in rows:
        code = segno.make(row['url'], error='m', boost_error=False)
        code.save(str(out / f"{row['id']}.svg"), scale=10, border=4, dark='#000000', light='#ffffff')
        code.save(str(out / f"{row['id']}.png"), scale=10, border=4, dark='#000000', light='#ffffff')
        matrices[row['id']] = {'url': row['url'], 'title': row['title'],
                               'rows': [''.join('1' if cell else '0' for cell in line) for line in code.matrix]}
    (SERIES / 'production' / 'qr-matrices.json').write_text(json.dumps(matrices, indent=1) + '\n')
    print(f'Wrote {len(rows)} QR codes (SVG and PNG) to {out}; version {code.version} for the last one.')


if __name__ == '__main__':
    main()
