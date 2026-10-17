"""Render every segment of an episode and stitch them into one animatic, narrated when the audio exists.

Usage (from anywhere; needs the manim CLI, ffmpeg, and TeX on the PATH for MathTex):
    python3 video-series/production/render.py 1            # 1080p60 (-qh)
    python3 video-series/production/render.py 1 -ql        # quick 480p15 review
    python3 video-series/production/render.py 1 -ql 1.5    # one segment

Segment videos land in build/media/videos/epNN/<quality>/; the stitched file is
build/episodes/epNN-<quality>.mp4. When tools/narrate.py has generated the episode's
narration (build/narration/audio/epNN/), each segment's audio starts with its scene and is
padded with silence to the scene's length, and the stitched file carries that soundtrack.
Every full episode ends with the production credits card (credits.py), under silence.
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
    return re.findall(r'^class (Segment_\d+_\d+)\(Segment\b', source, re.M)


def duration(path):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                 str(path)], capture_output=True, text=True, check=True).stdout)


def soundtrack(episode, videos, credits):
    """One WAV of every segment's narration, each padded to its scene's length, then silence
    for the credits, or None when some segment has no narration yet."""
    audio = BUILD / 'narration' / 'audio' / f'ep{episode:02d}'
    clips = [audio / (v.stem.split('_', 1)[1].replace('_', '.') + '.mp3') for v in videos]
    if not all(c.exists() for c in clips):
        missing = [c.stem for c in clips if not c.exists()]
        if len(missing) < len(clips):
            print('no soundtrack: no narration for ' + ', '.join(missing))
        return None
    work = BUILD / 'narration' / 'mix' / f'ep{episode:02d}'
    work.mkdir(parents=True, exist_ok=True)
    parts = []
    for clip, video in zip(clips, videos):
        length = duration(video)
        part = work / (clip.stem + '.wav')
        # Sample-exact padding keeps every segment's narration aligned with its own scene.
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(clip), '-af', f'apad=whole_dur={length}',
                        '-t', f'{length}', '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(part)], check=True)
        parts.append(part)
    silence = work / 'credits.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono',
                    '-t', f'{duration(credits)}', '-c:a', 'pcm_s16le', str(silence)], check=True)
    parts.append(silence)
    listing = work / 'parts.txt'
    listing.write_text(''.join(f"file '{p}'\n" for p in parts))
    track = work / 'narration.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-c', 'copy', str(track)], check=True)
    return track


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
    jobs = [(PRODUCTION / f'ep{episode:02d}.py', name) for name in names]
    if not only:
        jobs.append((PRODUCTION / 'credits.py', 'Credits'))
    for script, name in jobs:
        print(f'rendering {name} ...', flush=True)
        run = subprocess.run(['manim', quality, '--progress_bar', 'none', '--media_dir', str(BUILD / 'media'),
                              str(script), name], env=env, capture_output=True, text=True)
        if run.returncode:
            print(run.stdout[-3000:], run.stderr[-3000:], sep='\n')
            return run.returncode
    if only:
        return 0
    videos = BUILD / 'media' / 'videos' / f'ep{episode:02d}' / QUALITY_DIRS[quality]
    credits = BUILD / 'media' / 'videos' / 'credits' / QUALITY_DIRS[quality] / 'Credits.mp4'
    listing = BUILD / 'episodes' / f'ep{episode:02d}-segments.txt'
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text(''.join(f"file '{videos / (n + '.mp4')}'\n" for n in names) + f"file '{credits}'\n")
    output = BUILD / 'episodes' / f'ep{episode:02d}-{QUALITY_DIRS[quality]}.mp4'
    silent = output.with_name(output.stem + '-silent.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-c', 'copy', str(silent)], check=True)
    track = soundtrack(episode, [videos / (n + '.mp4') for n in names], credits)
    if track:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(silent), '-i', str(track), '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(output)], check=True)
        silent.unlink()
    else:
        silent.replace(output)
    seconds = duration(output)
    print(f'{output} ({seconds / 60:.1f} min)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
