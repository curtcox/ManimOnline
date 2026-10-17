"""Render every QR card as it appears in the videos (1080p, bottom-right) and decode it.

Usage (needs the manim CLI and a Python with opencv-python-headless):
    python video-series/production/check_qr.py [qr-id ...]

A code passes when OpenCV decodes exactly the URL listed in qr-links.json.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2

PRODUCTION = Path(__file__).resolve().parent
LINKS = {row['id']: row['url'] for row in json.loads((PRODUCTION.parent / 'qr-links.json').read_text())}
SCENE = '''
import sys
sys.path.insert(0, {production!r})
from common import *

class QRCheck(Scene):
    def construct(self):
        self.add(Text("Background content", font_size=60), qr_card({qr_id!r}))
'''


def main(ids):
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for qr_id in ids or sorted(LINKS):
            source = Path(tmp) / 'qrcheck.py'
            source.write_text(SCENE.format(production=str(PRODUCTION), qr_id=qr_id))
            subprocess.run(['manim', '-qh', '-s', '--media_dir', tmp, '--disable_caching', str(source), 'QRCheck'],
                           check=True, capture_output=True)
            image = next(Path(tmp, 'images', 'qrcheck').glob('QRCheck*.png'))
            decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(image)))
            ok = decoded == LINKS[qr_id]
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {qr_id} {decoded or '(not decoded)'}")
            image.unlink()
    print(f'\n{failures} failure(s)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
