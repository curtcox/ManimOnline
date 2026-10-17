# Drawing with Code: Manim and ManimOnline

Scripts for an explanatory video series about Manim, the Python animation library,
and ManimOnline, the browser editor that runs a Manim-compatible subset without an
install. The series is built in the style of narrated math-explainer videos: one
calm narrator, a dark canvas, intuition before syntax, and every idea shown moving.
Frequent QR codes open the exact code on screen in ManimOnline.

This series is independent. It is not affiliated with 3Blue1Brown or Manim Community.
Do not use 3Blue1Brown's name, logo or "pi creature" characters in titles, thumbnails
or graphics. Manim's history may be described factually (episode 1 does).

## Audience and tracks

- **Main track (episodes 1–9)** is for curious beginners who know a little Python:
  variables, functions, a `for` loop and a class header. Each episode builds one idea
  in depth and ends with something to try.
- **Deep-dive track (episodes 10–12)** is for developers who want to know how a
  static website runs Python, how manim-lite measures its fidelity against Manim
  Community, and how a link or QR code can carry code with no server.
- **Episode 0** is a 90-second trailer.

## Episodes

| # | Title | Track | Target | QR codes |
|---|---|---|---|---|
| 0 | [Trailer: Drawing with code](episodes/00-trailer.md) | – | 1.5 min | 1 |
| 1 | [An animation is a program](episodes/01-an-animation-is-a-program.md) | Main | 14 min | 5 |
| 2 | [Mobjects: the nouns](episodes/02-mobjects-the-nouns.md) | Main | 15 min | 6 |
| 3 | [Animations: the verbs](episodes/03-animations-the-verbs.md) | Main | 16 min | 6 |
| 4 | [What is a shape, really?](episodes/04-what-is-a-shape-really.md) | Main | 16 min | 5 |
| 5 | [Words and equations](episodes/05-words-and-equations.md) | Main | 17 min | 5 |
| 6 | [Things that change](episodes/06-things-that-change.md) | Main | 16 min | 5 |
| 7 | [Graphs, areas and slopes](episodes/07-graphs-areas-and-slopes.md) | Main | 16 min | 5 |
| 8 | [Cameras and the third dimension](episodes/08-cameras-and-the-third-dimension.md) | Main | 16 min | 5 |
| 9 | [From sketch to shareable](episodes/09-from-sketch-to-shareable.md) | Main | 17 min | 5 |
| 10 | [Python in a browser tab](episodes/10-python-in-a-browser-tab.md) | Deep dive | 17 min | 5 |
| 11 | [Rebuilding an engine to match](episodes/11-rebuilding-an-engine-to-match.md) | Deep dive | 18 min | 5 |
| 12 | [Links that carry code](episodes/12-links-that-carry-code.md) | Deep dive | 16 min | 4 |

Topics that earned their own episode: Bézier curves and morphing (4), text and
formulas (5), updaters and ValueTrackers (6), coordinate systems and calculus (7),
cameras and 3D (8), the browser runtime (10), compatibility testing (11) and
content-addressed links (12).

## Reading a script

Each episode is a sequence of numbered segments (`### 3.4 Title · ≈ 1:30`). Inside a segment:

- **Visual.** paragraphs describe what the animator builds. Numbers in brackets
  (`[V3.4a]`) name individual shots for the edit.
- **On screen** code blocks show code exactly as it should appear on screen. They
  are always excerpts of a QR snippet, so viewers can scan and find the same lines.
- **QR qNN-MM** lines say when to show a QR code and for how long.
- Lines starting with `>` are **narration**, the only text sent to ElevenLabs.

Durations are estimates at 145 words per minute plus held visual beats. The
extraction tool reports the narrated word count per segment.

## Voice and narration

- One narrator throughout: warm, curious, unhurried, speaking to one viewer ("you").
  The voice is Curt Cox's own ElevenLabs voice, "Curt Cox 2"; do not clone or
  imitate any other presenter. It reads at about 185 words per minute, faster than
  the 145 the estimates assume, so measured segments come out about a quarter shorter.
- Narration is written to be spoken: code is read in plain words ("self dot play",
  "the shift method"), numbers are spelled when ambiguous, and symbols never appear.
- `<break time="0.8s" />` marks a deliberate pause. ElevenLabs' v2/Turbo/Flash models
  honour it; for models that do not, run the extractor with `--strip-breaks` and add
  the silence in the edit instead.
- Generate each segment separately so visual timing can be adjusted per segment.

### Pronunciation

Load [`pronunciations.pls`](pronunciations.pls) as an ElevenLabs pronunciation
dictionary. It uses alias rules, which work on every model:

| Written | Say |
|---|---|
| Manim | MAN-im (short for "math animation") |
| ManimOnline | MAN-im online |
| Pyodide | pie-OH-dide |
| Bézier | BEZ-ee-ay |
| LaTeX | LAY-tek |
| MathJax | math-jacks |
| NumPy | NUM-pie |
| modl | MOD-ul *(assumed; confirm with the modl author)* |
| SVG, CID, JSON | S-V-G, C-I-D, JAY-son |
| WebM | web-em |

Code words that are also English words (`animate`, `construct`, `Transform`) are left
as they are: text-to-speech reads them as ordinary English, so it may stress them
differently than programmers would (CON-struct instead of con-STRUCT). Math terms have
the same problem: the voice does not always say them as a mathematician would. Respellings and
phoneme tags were tried and proved unreliable, so the series says so instead (see
below) rather than fighting the voice model.

## How this series was made

The series discloses how it was produced in three places, and they should agree:

- **Episode 1, segment 1.8** says the narration is synthetic and that code words and math
  terms may be pronounced differently than programmers or mathematicians would say them.
- **Every episode ends with a credits card** (`production/credits.py`, appended by
  `production/render.py` after the closing teaser, about 10 seconds, no narration).
- **Every video description** ends with the block below.

```text
How this series was made
Animation: Manim Community, from Python code in the series repository.
Scripts, animation code and production tooling: Claude Opus 5.5, an AI model by Anthropic.
Direction: Curt Cox.
Narration: ElevenLabs text-to-speech, from a model of Curt Cox's voice.
Source: https://github.com/curtcox/ManimOnline/tree/main/video-series

Text-to-speech reads names from code and terms from math as ordinary English words, so the
words you hear in these videos may be pronounced differently than programmers or
mathematicians would say them.
```

## Visual language

- **Canvas.** Manim's default near-black background. 16:9 at 1920×1080, 60 fps for
  production renders (ManimOnline previews are 15 fps; say so where it matters).
- **Colour roles.** Blue for objects as they are, yellow for whatever the narration
  is pointing at, green for "after" or "correct", red for errors and warnings, grey
  for scaffolding. Use Manim's named colours so on-screen code matches the picture.
- **Code panels.** Use Manim's `Code` mobject (monokai or a similar dark theme) on
  the left third; highlight the line being discussed with a yellow
  `SurroundingRectangle`. Never show more than about 14 lines at once.
- **Editor footage.** Screen recordings of ManimOnline at 1920×1080, browser zoom
  125 %, with the toolbar visible. Record the deployed site so it matches what QR
  codes open. Cursor movements should be slow and deliberate.
- **Recurring motif.** The "edit → render → preview" loop appears as three rounded
  boxes joined by arrows; episodes highlight the box they are about.

## QR codes

Every QR code is a HashBin link: `https://curtcox.github.io/ManimOnline/#<CID>`.
Opening it loads the snippet into the editor and renders it. The CID is computed from
the snippet's bytes, so **the URLs in [`qr-links.md`](qr-links.md) are already final**,
but they only resolve after the payloads are uploaded.

On screen:

- Bottom-right corner, at least 22 % of the frame height (about 240 px at 1080p),
  black on white with the full quiet zone. Never put a QR code over moving content.
- Hold each code for at least 6 seconds, with a caption above it in the episode's
  font: the QR id and the snippet title (for example "q03-03 · Two kinds of rotation").
- Each episode ends with a "QR wall" of all its codes for 10 seconds, and every
  episode description lists the same URLs in order.

Workflow:

1. Edit snippets in `snippets/`, then run the checks:
   ```bash
   python3 video-series/tools/check_snippets.py
   ```
   Use a Python with NumPy, Pillow and networkx (as CI uses) so every snippet can run.
   This native pass does not prove browser playback; open each link in a browser too.
2. Regenerate links (changing a single byte of a snippet changes its CID and QR code):
   ```bash
   node video-series/tools/qr-links.mjs --payloads video-series/build/payloads
   ```
3. Upload every payload that needs it. The simplest route is the editor itself: open
   each editor link from `build/payloads/editor-links.tsv`, confirm the Scene field
   matches the manifest (blank, except `q09-01`, which saves `Middle`), do not drag
   modl nodes (`q09-04`'s link pins its layout), choose
   **Save to HashBin**, and confirm that the returned CID equals the expected one.
   Saving spends HashBin account funds; choose a long retention period, because an
   expired payload breaks a printed QR code. Inline payloads (64 bytes or fewer, such
   as `q12-03`) need no upload: their content is inside the CID.
4. Confirm that everything resolves:
   ```bash
   node video-series/tools/qr-links.mjs --check
   ```
5. Make the QR images for the production scenes (needs `pip install segno`):
   ```bash
   python3 video-series/tools/make_qr_svgs.py
   ```

## Production pipeline

1. **Narration.** Generate each segment's audio with ElevenLabs:
   ```bash
   python3 video-series/tools/narrate.py 1
   ```
   The API key comes from the macOS keychain (service `elevenlabs`, or set
   `ELEVENLABS_KEYCHAIN_SERVICE`); `--dry-run` shows the text without spending credits.
   Pronunciation aliases from `pronunciations.pls` are applied to the text, and unchanged
   segments are not generated again. Audio goes to `build/narration/audio/epNN/`
   (gitignored), and the measured lengths to `build/narration/durations.json`.
   `node video-series/tools/extract-narration.mjs` still writes plain-text narration
   and the `cues.csv` cue sheet.
2. **Graphics.** Build the production scenes in Manim Community from the **Visual**
   notes; see [`production/README.md`](production/README.md) (the trailer and all twelve
   episodes are done and narrated; episode 1 is the template). Where a shot reproduces a QR snippet, start from the snippet's code. If
   a production scene stays within what ManimOnline supports, consider adding it as
   an extra QR code: viewers can then open the very animation they are watching.
3. **Timing.** The scenes read `durations.json`, so rendering after step 1 fits each scene
   to its audio, and `production/render.py` lays the narration under the stitched video.
4. **Editor footage.** `tools/record_footage.cjs` records the screen recordings from the deployed
   site, timed to the narration, and `render.py` composes them into their segments (see
   production/README.md). The stitched files in `build/episodes/` are then complete.
5. **Publishing.** `tools/youtube.py` writes each episode's YouTube files (title, description with
   chapters and QR links, tags, captions, thumbnail) to `youtube/`; see `youtube/README.md`.

## Keeping it accurate

ManimOnline's runtime is manim-lite, a compatibility subset, not Manim Community.
The scripts say so whenever it matters and never claim full compatibility. Before
recording, re-check episode statements that quote limits (15 fps previews, a 90-second
render deadline, 120 seconds or 1800 frames per preview, an 800 × 450 default preview,
the 32 MiB result limit) against `docs/rendering.md` and `AGENTS.md`, and re-run the
snippet checks after any ManimOnline release.

## Files

- `episodes/` – the scripts.
- `snippets/` – one source file per QR code (Manim `.py`, Graphviz `.dot`, modl `.modl`).
- `qr-manifest.json` – QR id, title, file, type and saved scene for each snippet.
- `qr-links.md`, `qr-links.json` – generated CIDs and final URLs.
- `pronunciations.pls` – ElevenLabs pronunciation dictionary.
- `tools/` – snippet checks, link generation, narration, caption timing, editor recordings and YouTube files.
- `youtube/` – per-episode upload files (title, description, tags, captions, thumbnail); see its README.
- `production/` – Manim Community scenes for the graphics, one Scene per segment.
  `production/credits.py` is the closing credits card shared by every episode.
