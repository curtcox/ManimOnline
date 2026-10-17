"""Render every segment of an episode and stitch them into one animatic, narrated when the audio exists.

Usage (from anywhere; needs the manim CLI, ffmpeg, and TeX on the PATH for MathTex):
    python3 video-series/production/render.py 1            # 1080p60 (-qh)
    python3 video-series/production/render.py 1 -ql        # quick 480p15 review
    python3 video-series/production/render.py 1 -ql 1.5    # one segment
    python3 video-series/production/render.py 1 --stitch   # compose and stitch existing segment videos again

Segment videos land in build/media/videos/epNN/<quality>/; the stitched file is
build/episodes/epNN-<quality>.mp4. When tools/narrate.py has generated the episode's
narration (build/narration/audio/epNN/), each segment's audio starts with its scene and is
padded with silence to the scene's length, and the stitched file carries that soundtrack.
Every full episode ends with the production credits card (credits.py), under silence.

Segments that show a screen recording (Segment.footage_in) render with a transparent background
(.mov); compose() lays each recorded clip (build/footage/<clip>.mp4, tools/record_footage.cjs)
under the scene, on black, and writes the segment's .mp4 with Manim's own x264 settings, so the
stitch can still copy streams. A missing clip leaves its screen black and prints a note.
"""
import json
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


def footage_segments(episode):
    """Segment classes that call footage_in: these render transparent and are composed."""
    source = (PRODUCTION / f'ep{episode:02d}.py').read_text()
    blocks = re.split(r'^(?=class )', source, flags=re.M)
    return {re.match(r'class (\w+)', b).group(1) for b in blocks
            if re.match(r'class Segment_\d+_\d+\(Segment\b', b) and 'self.footage_in(' in b}


def compose(episode, name, videos):
    """Lay the scene's recorded clips under its transparent render; returns the .mp4 path."""
    scene = videos / f'{name}.mov'
    output = videos / f'{name}.mp4'
    segment = name.split('_', 1)[1].replace('_', '.')
    slots = json.loads((BUILD / 'footage' / f'ep{episode:02d}-{segment}.json').read_text())
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                       'stream=width,height,r_frame_rate', '-of', 'json', str(scene)],
                                      capture_output=True, text=True, check=True).stdout)['streams'][0]
    width, height, rate = probe['width'], probe['height'], probe['r_frame_rate']
    length = duration(scene)
    frame_w, frame_h = slots['frame']
    inputs, chains, last = ['-i', str(scene)], [f'color=c=black:s={width}x{height}:r={rate}:d={length}[bg0]'], 'bg0'
    for k, slot in enumerate(slots['slots']):
        clip = BUILD / 'footage' / f"{slot['clip']}.mp4"
        if not clip.exists():
            print(f"{segment}: no recording {clip.name} yet; its screen stays black")
            continue
        meta = json.loads(clip.with_suffix('.json').read_text())
        left, top, w, h = slot['rect']
        x, y = (left + frame_w / 2) / frame_w * width, (frame_h / 2 - top) / frame_h * height
        w, h = round(w / frame_w * width / 2) * 2, round(h / frame_h * height / 2) * 2
        inputs += ['-itsoffset', f"{meta['start']}", '-i', str(clip)]
        crop = ''
        if slot.get('crop'):
            cx, cy, cw, ch = meta['crops'][slot['crop']]
            crop = f'crop={cw}:{ch}:{cx}:{cy},'
        end = slot.get('end', length)
        fades = f"fade=t=in:st={slot['start']}:d={slot['fade_in']}:alpha=1"
        if 'end' in slot:
            fades += f",fade=t=out:st={end}:d={slot['fade_out']}:alpha=1"
        opacity = f",colorchannelmixer=aa={slot['opacity']}" if 'opacity' in slot else ''
        chains.append(f'[{inputs.count("-i") - 1}:v]{crop}scale={w}:{h}:flags=lanczos:out_range=tv,format=yuva420p,'
                      f'{fades}{opacity}[clip{k}]')
        chains.append(f'[{last}][clip{k}]overlay=x={round(x)}:y={round(y)}:eof_action=pass[bg{k + 1}]')
        last = f'bg{k + 1}'
    chains.append(f'[{last}][0:v]overlay=format=auto,format=yuv420p[out]')
    # Manim's own encoder settings (libx264, crf 23, yuv420p): stitched segments share one stream layout.
    # Recordings decode as full-range (JPEG) video; out_range=tv above keeps every segment limited-range,
    # since the stitch copies the first segment's range flag onto the whole episode.
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(chains), '-map', '[out]',
                    '-t', f'{length}', '-r', rate, '-c:v', 'libx264', '-crf', '23', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', str(output)], check=True)
    return output


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
    stitch = '--stitch' in argv[1:]
    names = segments(episode)
    if only:
        names = [n for n in names if n.split('_', 1)[1].replace('_', '.') in only]
    env = None
    if TEX.exists() and not shutil.which('latex'):
        import os
        env = {**os.environ, 'PATH': f'{TEX}:{os.environ["PATH"]}'}
    footage = footage_segments(episode)
    jobs = [(PRODUCTION / f'ep{episode:02d}.py', name) for name in names]
    if not only:
        jobs.append((PRODUCTION / 'credits.py', 'Credits'))
    for script, name in [] if stitch else jobs:
        print(f'rendering {name} ...', flush=True)
        transparent = ['-t'] if name in footage else []
        run = subprocess.run(['manim', quality, *transparent, '--progress_bar', 'none', '--media_dir', str(BUILD / 'media'),
                              str(script), name], env=env, capture_output=True, text=True)
        if run.returncode:
            print(run.stdout[-3000:], run.stderr[-3000:], sep='\n')
            return run.returncode
    videos = BUILD / 'media' / 'videos' / f'ep{episode:02d}' / QUALITY_DIRS[quality]
    for name in names:
        if name in footage:
            compose(episode, name, videos)
    if only:
        return 0
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
