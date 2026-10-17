"""Write each episode's YouTube files: title, description (chapters, QR links, credits), tags,
English captions and thumbnail.

Usage (from anywhere; needs ffprobe, and for --thumbnails the manim CLI and TeX):
    python3 video-series/tools/youtube.py [episode ...] [--thumbnails]

Reads the authored copy in youtube/episodes.json, the episode scripts (segment titles, narration),
the narration sidecars' character timings (tools/narrate.py; tools/align_narration.py for episodes
1-6) and the stitched segment list build/episodes/epNN-segments.txt (render.py), so run it after
the episode's final render. Writes youtube/NN-slug/: title.txt, description.txt, tags.txt,
captions.en.srt and thumbnail.png (with --thumbnails, from production/thumbnails.py).

Captions are the script's narration as written (Manim, not the pronunciation alias Mannim), timed
word by word from the audio and offset by each segment's start in the stitched video.
"""
import json
import re
import shutil
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import narrate  # noqa: E402  (segments(), aliases(), spoken(); nothing is sent anywhere)

SERIES = TOOLS.parent
BUILD = SERIES / 'build'
OUT = SERIES / 'youtube'
META = json.loads((OUT / 'episodes.json').read_text())
TEX = Path.home() / 'Library' / 'TinyTeX' / 'bin' / 'universal-darwin'
LINE = 42                   # characters per caption line, two lines per cue
CUE_SECONDS = 6.0



def unwrapped(block):
    """The README's credits block with its prose paragraphs joined back into single lines."""
    paragraphs = []
    for para in block.strip().split('\n\n'):
        lines = para.split('\n')
        listed = all(re.match(r'^[A-Z][\w ,]*: ', line) for line in lines[1:]) and len(lines) > 1
        paragraphs.append(para if listed else ' '.join(lines))
    return '\n\n'.join(paragraphs)


CREDITS = unwrapped(re.search(r'```text\n(How this series was made.*?)```', (SERIES / 'README.md').read_text(), re.S).group(1))


def duration(path):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                 str(path)], capture_output=True, text=True, check=True).stdout)


def stitched(episode):
    """[(segment id, start, length)] of the stitched episode, the credits card last (id None)."""
    listing = BUILD / 'episodes' / f'ep{episode:02d}-segments.txt'
    rows, start = [], 0.0
    for path in re.findall(r"file '(.*)'", listing.read_text()):
        path = Path(path)
        match = re.match(r'Segment_(\d+)_(\d+)', path.stem)
        length = duration(path)
        rows.append((f'{match.group(1)}.{match.group(2)}' if match else None, start, length))
        start += length
    return rows


def segment_titles(episode):
    text = narrate.episode_file(episode).read_text()
    return {sid: title.strip() for sid, title in re.findall(r'^### (\d+\.\d+)\s+(.*?)\s*·', text, re.M)}


def clock(seconds):
    seconds = int(seconds)
    h, m, s = seconds // 3600, seconds // 60 % 60, seconds % 60
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


def chapters(episode, rows):
    """YouTube chapters: start at 0:00, at least 10 s each (shorter ones join the one before)."""
    titles = segment_titles(episode)
    marks = []
    for sid, start, _ in rows:
        if sid is None:
            continue
        if marks and start - marks[-1][0] < 10:
            continue
        marks.append((start, titles[sid]))
    if marks and rows[-1][1] + rows[-1][2] - marks[-1][0] < 10 and len(marks) > 1:
        marks.pop()
    marks[0] = (0.0, marks[0][1])
    return [f'{clock(t)} {title}' for t, title in marks] if len(marks) >= 3 else []


# ---------------------------------------------------------------- captions

def norm(word):
    return re.sub(r'[^a-z0-9]', '', word.lower())


def timed_words(sidecar):
    """[(word, start, end)] of the spoken text, from its character timings."""
    data = json.loads(sidecar.read_text())
    chars, starts = data['alignment']['characters'], data['alignment']['starts']
    text = ''.join(chars)
    words = []
    for m in re.finditer(r'<[^>]*>|\S+', text):
        if m.group().startswith('<'):
            continue
        words.append([m.group(), starts[m.start()], None])
    audio = sidecar.with_suffix('.mp3')
    total = duration(audio)
    for i, w in enumerate(words):
        nxt = words[i + 1][1] if i + 1 < len(words) else total
        # A word ends when the next starts, unless a pause lies between: then allow its length.
        w[2] = min(nxt, w[1] + 0.12 + 0.075 * len(w[0]))
    return words


def written_words(episode, sid, heard):
    """The script's own words with times taken from the spoken words they correspond to."""
    text = re.sub(r'<[^>]+>', ' ', narrate.segments(episode)[sid])
    paragraphs = [p.split() for p in text.split('\n\n')]
    ours = [(w, k) for k, para in enumerate(paragraphs) for w in para]
    a = [norm(w) for w, _ in ours]
    b = [norm(w) for w, _, _ in heard]
    times = [None] * len(ours)
    for block in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            times[block.a + k] = tuple(heard[block.b + k][1:])
    i = 0
    while i < len(times):                 # aliases ("Mannim Online" for "ManimOnline") share their gap
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(times) and times[j] is None:
            j += 1
        left = times[i - 1][1] if i else (heard[0][1] if heard else 0.0)
        right = times[j][0] if j < len(times) else (heard[-1][2] if heard else left + 1)
        step = max(right - left, 0.2) / (j - i)
        for k in range(i, j):
            times[k] = (left + step * (k - i), left + step * (k - i + 1))
        i = j
    return [(w, para, start, end) for (w, para), (start, end) in zip(ours, times)]


def wrap(text):
    if len(text) <= LINE:
        return text
    words = text.split()
    best = None
    for k in range(1, len(words)):
        a, b = ' '.join(words[:k]), ' '.join(words[k:])
        score = max(len(a), len(b))
        if best is None or score < best[0]:
            best = (score, a, b)
    return f'{best[1]}\n{best[2]}'


def cues(words, offset):
    """Group (word, paragraph, start, end) into caption cues of at most two lines and six seconds."""
    out, current = [], []

    def flush():
        if current:
            out.append([current[0][2] + offset, current[-1][3] + offset, ' '.join(w for w, *_ in current)])
            current.clear()

    for i, word in enumerate(words):
        if current:
            text = ' '.join(w for w, *_ in current)
            longer = len(text) + 1 + len(word[0])
            sentence_end = re.search(r'[.?!:]["”)]?$', current[-1][0]) and len(text) >= 18
            clause_end = re.search(r'[,;]$', current[-1][0]) and len(text) >= 30
            too_long = longer > 2 * LINE - 4 or word[3] - current[0][2] > CUE_SECONDS
            if word[1] != current[-1][1] or sentence_end or clause_end:
                flush()
            elif too_long:
                # Break after the last comma if there is one, so phrases stay together.
                commas = [k for k, w in enumerate(current[:-1]) if re.search(r'[,;:]$', w[0]) and k >= 2]
                rest = current[commas[-1] + 1:] if commas else []
                del current[len(current) - len(rest):]
                flush()
                current.extend(rest)
        current.append(word)
    flush()
    return out


def srt(all_cues):
    lines = []
    for n, (start, end, text) in enumerate(all_cues, 1):
        lines += [str(n), f'{stamp(start)} --> {stamp(end)}', wrap(text), '']
    return '\n'.join(lines)


def stamp(t):
    ms = int(round(t * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def captions(episode, rows):
    all_cues = []
    for sid, start, length in rows:
        if sid is None:
            continue
        sidecar = BUILD / 'narration' / 'audio' / f'ep{episode:02d}' / f'{sid}.json'
        heard = timed_words(sidecar)
        segment_cues = cues(written_words(episode, sid, heard), start)
        for cue in segment_cues:
            cue[1] = min(cue[1], start + length)
        all_cues += segment_cues
    for a, b in zip(all_cues, all_cues[1:]):    # hold a cue until the next one, within 1.5 s of silence
        a[1] = min(max(a[1], min(b[0], a[1] + 1.5)), b[0])
        if a[1] - a[0] < 0.7:
            a[1] = min(a[0] + 0.7, b[0])
    return srt(all_cues)


# ---------------------------------------------------------------- text

def clean(text):
    """YouTube refuses angle brackets in titles and descriptions."""
    return text.replace('<', '‹').replace('>', '›')


def description(episode, rows):
    info = META['episodes'][str(episode)]
    series = META['series']
    links = [row for row in json.loads((SERIES / 'qr-links.json').read_text()) if row['episode'] == episode]
    parts = [info['summary']]
    if links:
        parts.append('Open the code from this video in your browser (the QR codes on screen):\n' +
                     '\n'.join(f"{row['id']} · {row['title']}: {row['url']}" for row in links))
    marks = chapters(episode, rows)
    if marks:
        parts.append('Chapters\n' + '\n'.join(marks))
    number = 'the trailer' if episode == 0 else f'episode {episode} of 12'
    neighbours = []
    if episode > 1:
        neighbours.append(f"Previous: {META['episodes'][str(episode - 1)]['title']}")
    if 0 < episode < 12:
        neighbours.append(f"Next: {META['episodes'][str(episode + 1)]['title']}")
    parts.append(f"This is {number} of {series['name']}.\n" + ''.join(n + '\n' for n in neighbours) +
                 f"ManimOnline, the editor: {series['editor']}\n"
                 f"Sample gallery: {series['gallery']}\n"
                 f"Manim Community, the Python library: https://www.manim.community/")
    parts.append('This series is independent. It is not affiliated with 3Blue1Brown or Manim Community.')
    parts.append(CREDITS)
    return clean('\n\n'.join(parts)) + '\n'


def tags(episode):
    chosen, seen = [], set()
    for tag in META['episodes'][str(episode)]['tags'] + META['series']['tags']:
        if tag.lower() in seen:
            continue
        cost = len(tag) + (2 if ' ' in tag else 0) + (1 if chosen else 0)   # YouTube counts quotes and commas
        if sum(len(t) + (2 if ' ' in t else 0) for t in chosen) + len(chosen) + cost > 480:
            break
        chosen.append(tag)
        seen.add(tag.lower())
    return chosen


def thumbnail(episode, folder):
    env = None
    if TEX.exists() and not shutil.which('latex'):
        import os
        env = {**os.environ, 'PATH': f'{TEX}:{os.environ["PATH"]}'}
    script = SERIES / 'production' / 'thumbnails.py'
    names = (['Surface_8'] if episode == 8 else []) + [f'Thumb_{episode}']
    for name in names:
        subprocess.run(['manim', '-s', '-r', '1280,720', '--progress_bar', 'none', '--media_dir', str(BUILD / 'media'),
                        str(script), name], env=env, check=True, capture_output=True)
    image = sorted((BUILD / 'media' / 'images' / 'thumbnails').glob(f'Thumb_{episode}_*.png'))[-1]
    shutil.copy(image, folder / 'thumbnail.png')


def main(argv):
    episodes = [int(a) for a in argv if not a.startswith('-')] or range(13)
    for episode in episodes:
        folder = OUT / narrate.episode_file(episode).stem
        folder.mkdir(parents=True, exist_ok=True)
        rows = stitched(episode)
        info = META['episodes'][str(episode)]
        if len(info['title']) > 100:
            raise SystemExit(f'episode {episode}: title over 100 characters')
        (folder / 'title.txt').write_text(clean(info['title']) + '\n')
        text = description(episode, rows)
        if len(text) > 5000:
            raise SystemExit(f'episode {episode}: description over 5000 characters ({len(text)})')
        (folder / 'description.txt').write_text(text)
        (folder / 'tags.txt').write_text(', '.join(tags(episode)) + '\n')
        (folder / 'captions.en.srt').write_text(captions(episode, rows))
        if '--thumbnails' in argv:
            thumbnail(episode, folder)
        total = rows[-1][1] + rows[-1][2]
        print(f'{folder.relative_to(SERIES)}: {clock(total)}, {len(chapters(episode, rows))} chapters, '
              f'description {len(text)} characters')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
