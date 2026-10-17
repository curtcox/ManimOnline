# YouTube upload package

One folder per video, in upload order. Each folder has everything YouTube asks for except the video
itself, which is `build/episodes/epNN-1080p60.mp4` (gitignored; `production/render.py` makes it):

| File | Where it goes in YouTube Studio |
|---|---|
| `title.txt` | Title (100 characters at most) |
| `description.txt` | Description: summary, the episode's QR links, chapters, series links, credits |
| `tags.txt` | Tags (comma-separated, under YouTube's 500-character limit) |
| `thumbnail.png` | Thumbnail (1280 × 720) |
| `captions.en.srt` | Subtitles → Upload file → **With timing**, language English |

The chapters in each description start at 0:00 and are at least 10 seconds long, so YouTube shows
them on the progress bar without further setup.

## Regenerating

```bash
python3 video-series/tools/youtube.py              # titles, descriptions, tags, captions
python3 video-series/tools/youtube.py 4 --thumbnails   # one episode, with its thumbnail
```

The copy you would edit by hand is in [`episodes.json`](episodes.json): each episode's title,
summary, tags and thumbnail words, plus the playlist's title and description. Everything else comes
from the episode scripts, `qr-links.json`, the README's "How this series was made" block, and the
final render. So re-run it after any re-render: chapter times and caption offsets come from the
stitched segment lengths. Thumbnails are drawn by `production/thumbnails.py`.

Captions are the narration exactly as written in the scripts ("Manim", where the voice was sent the
alias "Mannim"), timed word by word. Episodes 0 and 7–12 use ElevenLabs' own character timings;
episodes 1–6 were narrated before those were saved, so `tools/align_narration.py` timed them with a
local speech recogniser. Spot checks (transcribing the stitched audio at a cue's start time) heard the cue's words.

## Before publishing

1. **Upload the QR payloads to HashBin first.** Every description lists the episode's QR links, and
   they only open after their payloads are saved (see the series README, "QR codes"). Saving spends
   HashBin account funds, so it is done by hand. Then check them all:
   ```bash
   node video-series/tools/qr-links.mjs --check
   ```
   `q12-03` is an inline link and works already.
2. Watch each video once at full size. The editor recordings in 0.2, 1.4, 1.7, 9.2 and 11.1 were
   captured from the deployed site on 17 October 2026; re-record them (`tools/record_footage.cjs`)
   if the editor's interface has changed since.

## Settings for every video

- **Playlist:** create one with the `playlist_title` and `playlist_description` from `episodes.json`,
  and add the videos in folder order (trailer first).
- **Audience:** No, it's not made for kids.
- **Category:** Education. **Video language** and **caption language:** English.
- **Altered or synthetic content:** the narration is a text-to-speech model of Curt Cox's voice. The
  descriptions say so; answering Yes to YouTube's disclosure question is the cautious choice.
- **Channel trailer:** the trailer (`00-trailer`) suits the channel's "for new visitors" slot.
- **End screen:** each episode ends with a 10-second credits card with no narration, a good place for
  an end screen linking the next episode.

Do not use 3Blue1Brown's name, logo or characters in titles, tags or thumbnails (see the series
README); the descriptions state that the series is independent.
