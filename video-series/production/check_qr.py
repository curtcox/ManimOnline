"""Render every QR card as it appears in the videos (1080p, bottom-right) and decode it.

Usage (needs the manim CLI and a Python with opencv-python-headless):
    python video-series/production/check_qr.py [qr-id ...]
    python video-series/production/check_qr.py --wall 2 [video]

A code passes when OpenCV decodes exactly the URL listed in qr-links.json. --wall
checks an episode's closing QR wall in its rendered last segment (1080p60 by default):
it samples frames, crops every QR code separately and decodes each one.
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


def check_wall(episode, video=None):
    import re
    source = (PRODUCTION / f'ep{episode:02d}.py').read_text()
    last = re.findall(r'^class (Segment_\d+_\d+)\(Segment\)', source, re.M)[-1]
    video = Path(video) if video else PRODUCTION.parent / 'build' / 'media' / 'videos' / f'ep{episode:02d}' / '1080p60' / f'{last}.mp4'
    expected = {qr_id for qr_id in LINKS if qr_id.startswith(f'q{episode:02d}-')}
    urls = {url: qr_id for qr_id, url in LINKS.items()}
    found = set()
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-vf', 'fps=1', str(Path(tmp) / 'f%04d.png')], check=True)
        for frame in sorted(Path(tmp).glob('f*.png')):
            image = cv2.imread(str(frame))
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, white = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            count, _, stats, _ = cv2.connectedComponentsWithStats(white)
            squares = [s for s in stats[1:] if s[2] > 120 and abs(int(s[2]) - int(s[3])) < 8]
            if len(squares) < len(expected):
                continue
            for x, y, w, h, _ in squares:
                crop = image[max(0, y - 20):y + h + 20, max(0, x - 20):x + w + 20]
                decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(crop)
                if decoded in urls:
                    found.add(urls[decoded])
            if found >= expected:
                break
    for qr_id in sorted(expected):
        print(f"{'ok  ' if qr_id in found else 'FAIL'} {qr_id}")
    missing = expected - found
    print(f'\n{len(missing)} failure(s) in {video.name}')
    return 1 if missing else 0


if __name__ == '__main__':
    if sys.argv[1:2] == ['--wall']:
        sys.exit(check_wall(int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None))
    sys.exit(main(sys.argv[1:]))
