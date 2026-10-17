#!/usr/bin/env python3
"""Generate an episode's narration with ElevenLabs, one audio file per segment.

    python3 video-series/tools/narrate.py 1            # every segment of episode 1
    python3 video-series/tools/narrate.py 1 1.4 1.7    # only these segments
    python3 video-series/tools/narrate.py 1 --dry-run  # show the text and character counts

The API key is read from the macOS keychain (`security find-generic-password -w`), using the
service named by ELEVENLABS_KEYCHAIN_SERVICE (default: the first of "elevenlabs",
"ElevenLabs", "elevenlabs-api-key" that exists). It is never printed or written to disk.
The voice is looked up by name (ELEVENLABS_VOICE, default "Curt Cox 2").

Narration is the blockquote text of each "### <n.m>" section, paragraphs kept, with
`<break time="..."/>` pauses (honoured by eleven_multilingual_v2). The aliases in
pronunciations.pls are applied to the text before it is sent.

Output (gitignored): build/narration/audio/epNN/<segment>.mp3 plus a .json sidecar holding a
hash of everything that shaped the audio and ElevenLabs' character timings (`alignment`), which
production scenes use to place a beat at a spoken phrase (Segment.at). A segment whose hash is unchanged is not generated
again, so re-running costs nothing unless the script, voice or settings changed (use --force
to regenerate anyway). Each run measures every segment and updates
build/narration/durations.json, which the production scenes use for their timing.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SERIES = Path(__file__).resolve().parent.parent
NARRATION = SERIES / 'build' / 'narration'
API = 'https://api.elevenlabs.io'
VOICE = os.environ.get('ELEVENLABS_VOICE', 'Curt Cox 2')
MODEL = os.environ.get('ELEVENLABS_MODEL', 'eleven_multilingual_v2')
OUTPUT_FORMAT = 'mp3_44100_128'
SERVICES = ['elevenlabs', 'ElevenLabs', 'elevenlabs-api-key']


def episode_file(episode):
    matches = sorted((SERIES / 'episodes').glob(f'{episode:02d}-*.md'))
    if not matches:
        raise SystemExit(f'No script for episode {episode}')
    return matches[0]


def segments(episode):
    """{segment id: narration} in script order, paragraphs separated by blank lines."""
    found, current = {}, None
    for line in episode_file(episode).read_text().splitlines():
        heading = re.match(r'^### (\d+\.\d+)\s', line)
        if heading:
            current = found.setdefault(heading.group(1), [[]])
            continue
        if line.startswith('## '):
            current = None
        if current is None:
            continue
        if line.startswith('>'):
            text = line[1:].strip()
            if text:
                current[-1].append(text)
            elif current[-1]:
                current.append([])
        elif current[-1]:
            current.append([])
    return {sid: '\n\n'.join(' '.join(p) for p in paras if p) for sid, paras in found.items()}


def aliases():
    lexicon = (SERIES / 'pronunciations.pls').read_text()
    pairs = re.findall(r'<grapheme>(.*?)</grapheme>\s*<alias>(.*?)</alias>', lexicon)
    return sorted(pairs, key=lambda p: -len(p[0]))


def spoken(text, pairs):
    """Apply the lexicon's aliases outside of tags, longest graphemes first."""
    def replace(chunk):
        for grapheme, alias in pairs:
            chunk = re.sub(rf'(?<![\w-]){re.escape(grapheme)}(?!\w)', alias, chunk)
        return chunk
    return ''.join(part if part.startswith('<') else replace(part) for part in re.split(r'(<[^>]+>)', text))


def api_key():
    services = [os.environ['ELEVENLABS_KEYCHAIN_SERVICE']] if os.environ.get('ELEVENLABS_KEYCHAIN_SERVICE') else SERVICES
    for service in services:
        found = subprocess.run(['security', 'find-generic-password', '-s', service, '-w'],
                               capture_output=True, text=True)
        if found.returncode == 0 and found.stdout.strip():
            return found.stdout.strip()
    raise SystemExit('No ElevenLabs key in the keychain under ' + ', '.join(services)
                     + '; set ELEVENLABS_KEYCHAIN_SERVICE to its service name.')


def request(key, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, headers={
        'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': '*/*'})
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise SystemExit(f'ElevenLabs {path.split("?")[0]}: HTTP {error.code} {error.read()[:400].decode(errors="replace")}')


def voice_id(key):
    voices = json.loads(request(key, '/v1/voices'))['voices']
    for voice in voices:
        if voice['name'] == VOICE:
            return voice['voice_id']
    names = ', '.join(sorted(v['name'] for v in voices))
    raise SystemExit(f'No voice named {VOICE!r}. Available: {names}')


def seconds(path):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                 str(path)], capture_output=True, text=True, check=True).stdout)


def main(argv):
    episode = int(argv[0])
    only = [a for a in argv[1:] if not a.startswith('-')]
    force, dry = '--force' in argv, '--dry-run' in argv
    script = segments(episode)
    pairs = aliases()
    texts = {sid: spoken(text, pairs) for sid, text in script.items()}
    ids = list(texts)
    chosen = [sid for sid in ids if not only or sid in only]
    out = NARRATION / 'audio' / f'ep{episode:02d}'
    out.mkdir(parents=True, exist_ok=True)

    key = vid = None
    for sid in chosen:
        index = ids.index(sid)
        body = {
            'text': texts[sid],
            'model_id': MODEL,
            # Neighbouring segments steer intonation across the cuts.
            'previous_text': re.sub(r'<[^>]+>', '', texts[ids[index - 1]])[-600:] if index else None,
            'next_text': re.sub(r'<[^>]+>', '', texts[ids[index + 1]])[:600] if index + 1 < len(ids) else None,
        }
        body = {k: v for k, v in body.items() if v}
        digest = hashlib.sha256(json.dumps([VOICE, OUTPUT_FORMAT, body], sort_keys=True).encode()).hexdigest()
        audio, sidecar = out / f'{sid}.mp3', out / f'{sid}.json'
        if dry:
            print(f'--- {sid} ({len(texts[sid])} characters)\n{texts[sid]}\n')
            continue
        if audio.exists() and sidecar.exists() and not force and json.loads(sidecar.read_text()).get('hash') == digest:
            print(f'{sid}: unchanged')
            continue
        if key is None:
            key = api_key()
            vid = voice_id(key)
        print(f'{sid}: generating {len(texts[sid])} characters ...', flush=True)
        result = json.loads(request(key, f'/v1/text-to-speech/{vid}/with-timestamps?output_format={OUTPUT_FORMAT}', body))
        audio.write_bytes(base64.b64decode(result['audio_base64']))
        alignment = result.get('alignment') or {}
        sidecar.write_text(json.dumps({'hash': digest, 'voice': VOICE, 'model': MODEL, 'text': texts[sid],
                                       'alignment': {'characters': alignment.get('characters', []),
                                                     'starts': alignment.get('character_start_times_seconds', [])}},
                                      indent=1) + '\n')
    if dry:
        print(f'{sum(len(texts[s]) for s in chosen)} characters in {len(chosen)} segment(s)')
        return 0

    durations_file = NARRATION / 'durations.json'
    durations = json.loads(durations_file.read_text()) if durations_file.exists() else {}
    for sid in ids:
        audio = out / f'{sid}.mp3'
        if audio.exists():
            durations[f'{episode:02d}.{sid.split(".")[1]}'] = round(seconds(audio), 3)
    durations_file.write_text(json.dumps(dict(sorted(durations.items())), indent=1) + '\n')
    total = sum(v for k, v in durations.items() if k.startswith(f'{episode:02d}.'))
    print(f'{durations_file}: episode {episode} narration {total / 60:.1f} min')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
