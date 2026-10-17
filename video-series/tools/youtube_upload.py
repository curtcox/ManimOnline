#!/usr/bin/env python3
"""Stage the YouTube uploads in one folder and write a prompt for Claude in Chrome.

Usage:
    python3 video-series/tools/youtube_upload.py

Writes build/youtube-upload/ (gitignored):
    videos/NN-slug.mp4          hard links to build/episodes/epNN-1080p60.mp4, all 13 selectable at once
    thumbnails/NN-slug.png      copies of youtube/NN-slug/thumbnail.png
    captions/NN-slug.en.srt     copies of youtube/NN-slug/captions.en.srt
    chrome-prompt.md            the prompt, with every title, description and tag list embedded

Each video's file name (without .mp4) is the title YouTube gives its draft, which the prompt uses to
find the draft. Re-run after any re-render or after youtube.py, since the links and copies are
snapshots. Run youtube.py's checks first: this script only refuses missing or oversized files.
"""
import json
import os
import shutil
import sys
from pathlib import Path

SERIES = Path(__file__).resolve().parent.parent
YOUTUBE = SERIES / 'youtube'
OUT = SERIES / 'build' / 'youtube-upload'
FENCE = '````'


def stage():
    folders = sorted(p for p in YOUTUBE.iterdir() if p.is_dir() and p.name[:2].isdigit())
    if len(folders) != 13:
        raise SystemExit(f'expected 13 episode folders in {YOUTUBE}, found {len(folders)}')
    for sub in ('videos', 'thumbnails', 'captions'):
        shutil.rmtree(OUT / sub, ignore_errors=True)
        (OUT / sub).mkdir(parents=True)
    rows = []
    for folder in folders:
        slug = folder.name
        video = SERIES / 'build' / 'episodes' / f'ep{int(slug[:2]):02d}-1080p60.mp4'
        files = {name: folder / name for name in ('title.txt', 'description.txt', 'tags.txt', 'thumbnail.png', 'captions.en.srt')}
        missing = [str(p) for p in [video, *files.values()] if not p.exists()]
        if missing:
            raise SystemExit('missing: ' + ', '.join(missing))
        if files['thumbnail.png'].stat().st_size >= 2_000_000:
            raise SystemExit(f"{files['thumbnail.png']} is over YouTube's 2 MB thumbnail limit")
        staged = OUT / 'videos' / f'{slug}.mp4'
        try:
            os.link(video, staged)
        except OSError:
            shutil.copy2(video, staged)
        shutil.copy2(files['thumbnail.png'], OUT / 'thumbnails' / f'{slug}.png')
        shutil.copy2(files['captions.en.srt'], OUT / 'captions' / f'{slug}.en.srt')
        description = files['description.txt'].read_text().strip()
        if FENCE in description:
            raise SystemExit(f'{folder} description contains {FENCE}')
        rows.append({'slug': slug, 'title': files['title.txt'].read_text().strip(), 'description': description,
                     'tags': files['tags.txt'].read_text().strip()})
    return rows


def prompt(rows):
    series = json.loads((YOUTUBE / 'episodes.json').read_text())['series']
    out = OUT.resolve()
    lines = [
        f"# Upload \"{series['name']}\" to YouTube",
        '',
        'You are helping me upload a 13-video series to my YouTube channel in YouTube Studio',
        '(https://studio.youtube.com), using this Chrome window, where I am already signed in.',
        'Everything you need is below. Copy every title, description and tag list exactly as given:',
        'do not rewrite, shorten, translate or "improve" any of it.',
        '',
        '## Settings',
        '',
        '- Visibility for every video: **Private**. I will publish them myself later, so never choose',
        '  Public, Unlisted or Schedule, and never click Publish on a public setting.',
        f"- Playlist: **{series['playlist_title']}** (description below).",
        '- Audience: "No, it\'s not made for kids". Age restriction: none.',
        '- Altered or synthetic content: **Yes** (the narration is a text-to-speech model of my voice).',
        '- Category: **Education**. Video language: **English**.',
        '- Captions: upload the .srt file for each video as English subtitles **with timing**.',
        '- Leave everything else at YouTube\'s defaults (comments, license, automatic chapters, remixing).',
        '',
        '## Files on this computer',
        '',
        f'- Videos (one per episode): `{out}/videos/`',
        f'- Thumbnails (1280 x 720 PNG): `{out}/thumbnails/<name>.png`',
        f'- Captions: `{out}/captions/<name>.en.srt`',
        '',
        '`<name>` is the video\'s file name without `.mp4`, for example `03-animations-the-verbs`. YouTube',
        'names each uploaded draft after its file, so a draft titled `03-animations-the-verbs` is that episode.',
        '',
        'Attach thumbnails and captions with your file upload tool: find the page\'s hidden',
        '`input[type=file]` (do not click the button, which opens a native dialog you cannot see) and pass',
        'the absolute path. If the tool rejects a path, stop and ask me to give you access to the folder,',
        'or to choose that one file myself. The videos are too large for your upload tool, so I select them.',
        '',
        '## Steps',
        '',
        '1. **Check the channel.** Open YouTube Studio. If custom thumbnails are unavailable (the channel is',
        '   not verified; see https://www.youtube.com/verify), tell me and wait. Do not verify it yourself.',
        '2. **Create the playlist first.** In Studio: Content → Playlists → New playlist. Title and',
        '   description exactly as below, visibility Private. If a playlist with this title already exists,',
        '   use it and do not create a second one.',
        '3. **Ask me to upload the videos.** Click Create → Upload videos, then tell me: "Select all 13 files',
        f'   in {out}/videos/ in the file dialog." Wait until I say they are selected. YouTube',
        '   uploads them as drafts in the background. If YouTube reports a daily upload limit, tell me which',
        '   files it refused and carry on with the rest.',
        '4. **Fill in each draft, in order 00, 01, ... 12** (this order also sets the playlist order).',
        '   Open it from Content (or the upload dialog) with "Edit draft". On each page of the wizard:',
        '   - **Details:** replace the title with the one below. Click into the description box, select',
        '     everything in it, and type the description below, keeping every line break and blank line.',
        '     Upload the thumbnail. Choose the playlist. Choose "No, it\'s not made for kids".',
        '     Click "Show more": Altered content → Yes; Tags → paste the tag list as one comma-separated',
        '     line; Language and captions certification → Video language: English; Category: Education.',
        '   - **Video elements:** Add subtitles → Upload file → With timing → Continue, then attach the',
        '     caption file. Confirm the language is English and click Done. Skip end screens and cards.',
        '   - **Checks:** read the result. If there is a copyright claim or another problem, note it and go on.',
        '   - **Visibility:** Private → Save.',
        '   Then **verify** the saved video: reopen its Details and read back the title, the start and end of',
        '   the description, the tags, the thumbnail, the playlist and the subtitles. Fix any difference.',
        '   Descriptions are about 2,500 characters with long links, so check that none were cut off or',
        '   changed (YouTube\'s limit is 5,000; titles 100; tags 500).',
        '5. **Check the playlist.** Open it in Studio and confirm it holds all 13 videos in order 00 to 12;',
        '   drag any out-of-order video into place.',
        '6. **Report.** Give me a table: episode, title, the video\'s Studio link (or ID), and anything that',
        '   needs my attention (a failed upload, a missing thumbnail or caption, a check warning,',
        '   processing still running).',
        '',
        'Do not change any channel settings, delete anything, publish anything, or accept any new terms or',
        'agreements. If YouTube asks for any of those, or you are unsure, stop and ask me.',
        '',
        '## Playlist',
        '',
        f"Title: {series['playlist_title']}",
        '',
        'Description:',
        FENCE + 'text',
        series['playlist_description'],
        FENCE,
        '',
        '## The videos',
    ]
    for row in rows:
        lines += [
            '',
            f"### {row['slug']}",
            '',
            f"- Video: `{out}/videos/{row['slug']}.mp4`",
            f"- Thumbnail: `{out}/thumbnails/{row['slug']}.png`",
            f"- Captions: `{out}/captions/{row['slug']}.en.srt`",
            f"- Title: {row['title']}",
            f"- Tags: {row['tags']}",
            '',
            'Description:',
            FENCE + 'text',
            row['description'],
            FENCE,
        ]
    return '\n'.join(lines) + '\n'


def main():
    rows = stage()
    text = prompt(rows)
    (OUT / 'chrome-prompt.md').write_text(text)
    size = sum(f.stat().st_size for f in (OUT / 'videos').iterdir())
    print(f'Staged 13 videos ({size / 1e6:.0f} MB), thumbnails and captions in {OUT}; '
          f'wrote chrome-prompt.md ({len(text):,} characters).')


if __name__ == '__main__':
    sys.exit(main())
