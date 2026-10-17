"""Add character timings to narration sidecars that lack them, by aligning the known text to the audio.

Usage (needs a Python with faster-whisper: python3 -m venv v && v/bin/pip install faster-whisper):
    v/bin/python video-series/tools/align_narration.py [episode ...] [--redo]

tools/narrate.py saves ElevenLabs' character timings with every segment it generates, but the
sidecars of segments generated before it asked for them have none (episodes 1-6). This runs a
local speech recogniser (faster-whisper, no ElevenLabs credits) for its word timings, pairs its
words with the words of the spoken text the sidecar already holds, and writes an `alignment` in
narrate.py's format (one start time per character of that text), marked `alignment_source`.
Segment.at and tools/captions.py then work the same for every episode. Sidecars that already
have an alignment are left alone, so ElevenLabs' own timings always win; --redo re-aligns the ones
this tool wrote. Checked against ElevenLabs' timings (1.8, 8.3), word starts agree to a median of
0.07 s and within 0.25 s for 95 % of words.
"""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

SERIES = Path(__file__).resolve().parent.parent
AUDIO = SERIES / 'build' / 'narration' / 'audio'
MODEL = 'small.en'


def norm(word):
    return re.sub(r'[^a-z0-9]', '', word.lower())


def words_of(text):
    """(start, end) character spans of the whitespace-separated words of text."""
    return [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]


def align(text, heard, duration):
    """Character start times for text, given recognised words [(word, start, end)]."""
    spans = words_of(text)
    ours = [norm(text[a:b]) for a, b in spans]
    theirs = [norm(w) for w, _, _ in heard]
    times = [None] * len(spans)
    for block in SequenceMatcher(None, ours, theirs, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            _, start, end = heard[block.b + k]
            times[block.a + k] = (start, end)
    # Words the recogniser heard differently share the gap between their matched neighbours.
    i = 0
    while i < len(times):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(times) and times[j] is None:
            j += 1
        left = times[i - 1][1] if i else 0.0
        right = times[j][0] if j < len(times) else duration
        weights = [max(len(ours[k]), 1) for k in range(i, j)]
        step = (right - left) / sum(weights)
        t = left
        for k, w in zip(range(i, j), weights):
            times[k] = (t, t + w * step)
            t += w * step
        i = j
    starts = []
    word = 0
    for c in range(len(text)):
        while word < len(spans) and spans[word][1] <= c:
            word += 1
        if word < len(spans) and spans[word][0] <= c:
            a, b = spans[word]
            start, end = times[word]
            starts.append(round(start + (end - start) * (c - a) / (b - a), 3))
        else:
            starts.append(round(times[word - 1][1] if word else 0.0, 3))
    return starts


def main(argv):
    from faster_whisper import WhisperModel
    model = None
    redo = '--redo' in argv
    episodes = [int(a) for a in argv if not a.startswith('-')] or range(0, 13)
    for episode in episodes:
        for sidecar in sorted((AUDIO / f'ep{episode:02d}').glob('*.json')):
            data = json.loads(sidecar.read_text())
            if data.get('alignment', {}).get('starts') and not (redo and data.get('alignment_source')):
                continue
            model = model or WhisperModel(MODEL, device='cpu', compute_type='int8')
            text = re.sub(r'<[^>]+>', ' ', data['text'])
            # No initial_prompt: prompting with the script made it stop early on longer segments.
            segments, info = model.transcribe(str(sidecar.with_suffix('.mp3')), word_timestamps=True, vad_filter=False)
            heard = [(w.word, w.start, w.end) for s in segments for w in s.words]
            starts = align(text, heard, info.duration)
            data['alignment'] = {'characters': list(text), 'starts': starts}
            data['alignment_source'] = f'faster-whisper {MODEL}'
            sidecar.write_text(json.dumps(data, indent=1) + '\n')
            matched = sum(1 for w in heard if norm(w[0]))
            print(f'{sidecar.parent.name}/{sidecar.stem}: {len(words_of(text))} words, {matched} heard', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
