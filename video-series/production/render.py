"""Render every segment of an episode and stitch them into one silent animatic.

Usage (from anywhere; needs the manim CLI, ffmpeg, and TeX on the PATH for MathTex):
    python3 video-series/production/render.py 1            # 1080p60 (-qh)
    python3 video-series/production/render.py 1 -ql        # quick 480p15 review
    python3 video-series/production/render.py 1 -ql 1.5    # one segment

Segment videos land in build/media/videos/epNN/<quality>/; the stitched file is
build/episodes/epNN-<quality>.mp4. Audio is added later in the edit, segment by segment.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

PRODUCTION = Path(__file__).resolve().parent
SERIES = PRODUCTION.parent
BUILD = SERIES / 'build'
TEX = Path.home() / 'Library' / 'TinyTeX' / 'bin' / 'universal-darwin'
QUALITY_DIRS = {'-ql': '480p15', '-qm': '720p30', '-qh': '1080p60', '-qk': '2160p60'}


def segments(episode):
    source = (PRODUCTION / f'ep{episode:02d}.py').read_text()
    return re.findall(r'^class (Segment_\d+_\d+)\(Segment\)', source, re.M)


def main(argv):
    episode = int(argv[0])
    quality = next((a for a in argv[1:] if a.startswith('-q')), '-qh')
    only = [a for a in argv[1:] if not a.startswith('-')]
    names = segments(episode)
    if only:
        names = [n for n in names if n.split('_', 1)[1].replace('_', '.') in only]
    env = None
    if TEX.exists() and not shutil.which('latex'):
        import os
        env = {**os.environ, 'PATH': f'{TEX}:{os.environ["PATH"]}'}
    script = PRODUCTION / f'ep{episode:02d}.py'
    for name in names:
        print(f'rendering {name} ...', flush=True)
        run = subprocess.run(['manim', quality, '--progress_bar', 'none', '--media_dir', str(BUILD / 'media'),
                              str(script), name], env=env, capture_output=True, text=True)
        if run.returncode:
            print(run.stdout[-3000:], run.stderr[-3000:], sep='\n')
            return run.returncode
    if only:
        return 0
    videos = BUILD / 'media' / 'videos' / f'ep{episode:02d}' / QUALITY_DIRS[quality]
    listing = BUILD / 'episodes' / f'ep{episode:02d}-segments.txt'
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text(''.join(f"file '{videos / (n + '.mp4')}'\n" for n in names))
    output = BUILD / 'episodes' / f'ep{episode:02d}-{QUALITY_DIRS[quality]}.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-c', 'copy', str(output)], check=True)
    seconds = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                    str(output)], capture_output=True, text=True, check=True).stdout)
    print(f'{output} ({seconds / 60:.1f} min)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
