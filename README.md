# [ManimOnline](https://manim.hashbin.page/)

A static, in-browser editor for three languages, with live previews:

- **Manim** Python scenes, run in the browser by Pyodide through **Manim-lite**, a
  compatibility layer that follows Manim Community 0.22 closely but is not the full
  Community engine. See [rendering support and limitations](docs/rendering.md).
- **Graphviz DOT** diagrams, rendered by viz.js.
- **modl** diagrams, using the parser and SVG editor adapted from
  [curtcox/modl](https://github.com/curtcox/modl) (draggable nodes, image/link nodes,
  deep zoom).

The production app is <https://manim.hashbin.page/>. The GitHub Pages copy at
<https://curtcox.github.io/ManimOnline/> also serves the
[documentation](https://curtcox.github.io/ManimOnline/docs/) and
[gallery](https://curtcox.github.io/ManimOnline/gallery.html), and offers **Move saved
work** / **Download backup** for drafts saved there before the move. Transfers copy only
this app's documents and public settings and never copy HashBin credentials.

## Features

- Automatic language detection (strings and comments are ignored), with a **Renderer**
  override (Auto, Manim, Graphviz, modl) that is kept in links.
- Manim playback with play/pause, replay and seeking; scene selection; export of the
  current frame as SVG or PNG, or the whole animation as MP4 or WebM (WebCodecs, in memory).
- Graphviz engine/output selection and SVG/PNG download; modl SVG download.
- A [sample gallery](gallery.html) of 115 searchable samples (103 Manim, 6 DOT, 6 modl)
  with pre-rendered covers and MP4 previews that play without starting Python.
- Source links, QR codes, optional link shortening, HashBin Publish saves and a local
  library of named documents with revision history.
- Offline use after the first visit, with a separately cached Python/MathJax runtime.
- Optional AI review of proposed source changes (off by default, budgets start at zero).
- A phone layout that opens on the preview.

## Using the editor

Type in the code pane; detection updates after 300 ms of quiet and rendering starts
after one second. **Render** starts a Manim render immediately (also a retry after an
error or timeout); **Cancel** stops it and keeps the last completed preview. Changing the
renderer or pressing Enter in the scene field also renders immediately.

- **Manim:** write a `Scene` subclass after `from manim import *`. Leave the scene field
  empty to render the first scene in the file, or enter a class name. Previews run at
  15 fps, up to 120 seconds (1,800 frames), with a 90-second execution deadline and a
  32 MiB result limit. NumPy, Pillow, Pygments and networkx load only for sources that
  use them.
- **Graphviz:** for example `digraph { a -> b }`. Unbraced `a -> b` is detected as modl;
  add a graph header or force Graphviz for DOT fragments.
- **modl:** one node or edge per line, for example `a square blue Start`,
  `b circle green Finish`, `a -> b dashed purple Next`. See the
  [modl language documentation](https://curtcox.github.io/modl/docs/). Drag nodes to
  move them; positions (including fractional ones) are saved with links. The view zooms
  from 0.001× to 1000×: wheel to zoom under the cursor, drag the background or
  middle-drag to pan, and use **−**, **+** and **Reset view**. See
  [modl deep zoom](docs/modl-deep-zoom.md) for measurements and limits.

On phones (up to 760 px wide or 500 px tall) the app opens on the preview, with
**Preview**/**Code** tabs; less common controls are under **More**. Opening a Manim
gallery sample on a phone plays its MP4 and starts Python only after an edit, **Render**,
a scene or renderer change, or an export.

**Sample gallery** opens the gallery in a new tab. Search by title or filter by language;
**Load in editor** (or a `?example=<id>` link) opens a sample. Edits made while a sample
is loading are kept, and a failed load leaves the current source alone.

## Links, drafts and HashBin

Explicit program, source, example and CID links always open their document, whatever
drafts the browser holds. The bare homepage opens the default example. Local drafts are
kept separately: use **Resume saved work** to recover one. Opening or running a link
never overwrites saved work.

The **Library** keeps named documents with an explicit-save history (**Save**/**Save
as…**) in this browser's IndexedDB; names and descriptions stay local. The library or a
single revision can be exported to a file or HashBin and imported again with a preview.
Loading a library revision waits for **Render**.

**Share** captures the source, renderer, scene, Graphviz options and modl positions in
a local link, which can be shortened (is.gd through AllOrigins, ten-second limit; the
source link remains if that fails) or shown as a QR code. Older link formats remain
readable. See [sharing](docs/sharing.md).

**Save to HashBin** saves the same document through HashBin Publish: **Review on
HashBin** shows the size, retention, price and balance, and you approve the save on
hashbin.org. This app never holds a HashBin credential. Blocked popups fall back to a
redirect (sources up to 512 KiB) that restores the source on return. **Load from
HashBin** accepts a CID, a `https://256t.us/<cid>` link or a saved editor URL; `#<cid>`
URLs load automatically. Loads verify the bytes against the CID, are limited to 5 MiB
and 20 seconds, and are discarded if you edit first. Small content (up to 64 bytes) is
decoded from the CID itself.

Saved documents use `format: "hashbin-diagram"`, `version: 1`, `src` and `type`
(`graphviz`, `modl` or `manim`); modl adds `pos`, Manim adds `scene`, and Graphviz adds
`graphviz: {engine, format}`. The modl-only editor can read modl saves.

The registered **Manim Online** HashBin app uses the public client ID in the
`hashbin-client-id` meta tag of `index.html`. Its return address
`https://manim.hashbin.page/` must stay registered; another deployment needs its own
registered address or client. Rendering and public CID loading need no registration.

## Offline use

The application, gallery covers and documentation are cached atomically, and every byte
is checked against pinned SHA-256 hashes. Python and MathJax are cached separately after
the first live render (or **Save Python offline**). The status reads **Diagrams ready
offline** until that runtime is saved, then **Available offline**. Gallery videos, optional
package wheels and resources fetched by user scenes are not part of readiness. Updates
wait for **Update and reload**, which preserves source and preview settings. See
[offline use](docs/offline.md).

## Security model

All apps on a shared origin share its storage, so the app trusts only hash-verified
cached bytes and a strict Content-Security-Policy (no inline scripts). Scene code runs in
a Web Worker inside an opaque-origin sandbox iframe created by the HashBin SDK, so it
never runs with the app's origin, storage or credentials. Rendered SVG accepts only
inline base64 raster images, and SVG input rejects DTD entities.

## Optional AI

**Ask** proposes source changes that you review, accept or undo; accepted changes wait for
an explicit Render. Gallery suggestions and model comparison are also available. Nothing
is sent without consent, shared links never call a model, and budgets start at zero. See
[AI guidance](docs/ai.md). The bundled synthetic [suite](ai-suite.json) and
[comparison report](ai-comparison.json) measure source assertions and document
invariants, not runtime quality.

## Video series

[Drawing with Code: Manim and ManimOnline](https://www.youtube.com/playlist?list=PLXaiuWr3VAhk)
is a narrated YouTube series. Episodes 1–9 are for beginners who know a little Python;
episodes 10–12 explain how ManimOnline runs Python in the browser, matches Manim
Community, and stores code in links. QR codes in the videos open the code on screen in
the editor, which links back to the chapter that explains it; gallery samples covered by
an episode link to that chapter too. Scripts, snippets and production tooling are in
[`video-series/`](video-series/README.md).

| # | Episode |
|---|---|
| Trailer | [Drawing with Code: Manim and ManimOnline (Trailer)](https://www.youtube.com/watch?v=xz2KHjntJK4&list=PLXaiuWr3VAhk) |
| 1 | [An Animation Is a Program](https://www.youtube.com/watch?v=oZYsQfNCl7U&list=PLXaiuWr3VAhk) |
| 2 | [Mobjects: The Nouns](https://www.youtube.com/watch?v=uNAZ8IUrWGg&list=PLXaiuWr3VAhk) |
| 3 | [Animations: The Verbs](https://www.youtube.com/watch?v=2gHw0OI5Ewg&list=PLXaiuWr3VAhk) |
| 4 | [What Is a Shape, Really? Bézier Curves](https://www.youtube.com/watch?v=wLi02QRgJ3k&list=PLXaiuWr3VAhk) |
| 5 | [Words and Equations: Text, MathTex and Tex](https://www.youtube.com/watch?v=mqY9GnhD5iI&list=PLXaiuWr3VAhk) |
| 6 | [Things That Change: Updaters and ValueTrackers](https://www.youtube.com/watch?v=1xZ6yq3bn6M&list=PLXaiuWr3VAhk) |
| 7 | [Graphs, Areas and Slopes](https://www.youtube.com/watch?v=AcSK_JwYSRo&list=PLXaiuWr3VAhk) |
| 8 | [Cameras and the Third Dimension](https://www.youtube.com/watch?v=g5-rbmAx4pw&list=PLXaiuWr3VAhk) |
| 9 | [From Sketch to Shareable: ManimOnline Tour](https://www.youtube.com/watch?v=osZ8k7DiIdg&list=PLXaiuWr3VAhk) |
| 10 | [Python in a Browser Tab: Pyodide and WebAssembly](https://www.youtube.com/watch?v=FwW81F7Zx2o&list=PLXaiuWr3VAhk) |
| 11 | [Rebuilding an Engine to Match Manim](https://www.youtube.com/watch?v=Pjdinan5Xcg&list=PLXaiuWr3VAhk) |
| 12 | [Links That Carry Code: Compression, Hashes and QR Codes](https://www.youtube.com/watch?v=u7ArYmhyNxE&list=PLXaiuWr3VAhk) |

## Development

The site is buildless: serve the checkout as static files. Node 22.12+ and `npm ci` are
needed only for tooling and tests.

```bash
npm ci
```

```bash
npm run serve
```

Then open <http://localhost:8000/>. `python3 -m http.server 8000` also works.

Shared URL/document/CID handling, HashBin Publish, QR codes, drafts, the local library,
shortening,
application caching, the shell and mobile tabs, gallery filtering and AI come from the
immutable [Fragment Kit](vendor/fragment-kit-v0.5.0/) v0.5.0 pin; upgrade by vendoring a
new release, never by editing it. Manim-lite, the renderers, worker isolation and the
preview media producer belong to this app. [AGENTS.md](AGENTS.md) maps the code and its
invariants.

### Tests

```bash
npm test
```

```bash
npm run test:python
```

```bash
npm run check
```

`npm test` runs the Node unit tests and `npm run test:python` the Python tests (install
`numpy pillow pygments` to run the package-backed tests; without them those tests skip).
`npm run check` syntax-checks scripts and verifies that gallery previews, generated
docs, gallery and offline files and vendor pins are current. Unit tests do not prove
Pyodide loading or browser playback.

Browser suites use Playwright against the test server, which mirrors verified copies of
the pinned CDN files:

```bash
npx playwright install chromium firefox webkit
```

```bash
node scripts/fetch-runtime.mjs
```

```bash
PORT=8000 node tests/browser/server.cjs
```

```bash
BROWSER=chromium npm run test:browser
```

`test:browser` runs `cold-math`, `gallery`, `smoke`, `languages`, `modl-zoom`, `sharing`,
`touch` (Chromium only) and `upgrade`. CI also runs `ai.mjs`, `legacy-publish.cjs`,
`url-state.cjs` and the Fragment Kit contracts (`npm run test:contracts`). Each script
also accepts `<url> <browser...>` arguments, for example
`node tests/browser/smoke.cjs http://127.0.0.1:8000/ chromium webkit`. Playwright's
Firefox may fail to launch on recent macOS ("Could not find profile folder"); CI runs all
three engines on Ubuntu. Mocked suites spend no HashBin funds and do not prove live
HashBin registration or shortening-service availability.

### Generated files

- After changing any shipped asset, run `npm run offline` to regenerate
  `offline-assets.js` (hashes and content version).
- After editing `docs/*.md`, run `npm run docs` to regenerate `docs/*.html`.
- After changing a Manim sample or the runtime, serve the checkout and run
  `node scripts/render-gallery.cjs http://localhost:8000/ [example IDs...]` to rebuild
  covers and MP4 previews in `gallery/previews/` (unchanged ones are skipped by
  fingerprint). Then run `node scripts/gallery-catalog.mjs` (writes
  `src/gallery-catalog.js`) and `npm run gallery` (Fragment Kit covers in
  `gallery/covers/`) when the catalog or covers change.
- `src/video-links.js` is generated by `video-series/tools/youtube.py`.

CI (`.github/workflows/test.yml`) runs the shared Fragment Kit gates, the Python tests and
the browser suites in Chromium, Firefox and WebKit; `deploy.yml` publishes after they pass.

## Documentation

- [Rendering support and limitations](docs/rendering.md)
- [Completion and acceptance](docs/completion.md)
- [Sharing and QR codes](docs/sharing.md) · [Offline use](docs/offline.md) · [Optional AI](docs/ai.md)
- [modl deep zoom](docs/modl-deep-zoom.md)
- [AGENTS.md](AGENTS.md) for contributors and coding agents.
- [`examples/`](examples/) holds the gallery scenes; its Markdown files describe the
  broader Manim API and do not imply browser support.

## Credits

- Based on [GraphvizOnline](https://github.com/dreampuf/GraphvizOnline) by Dreampuf (BSD-3-Clause)
- [viz.js](https://github.com/mdaines/viz.js) for Graphviz rendering
- [Pyodide](https://pyodide.org/) for browser Python execution
- [MathJax](https://www.mathjax.org/) and [typst.ts](https://github.com/Myriad-Dreamin/typst.ts) for formulas
- [ACE Editor](https://ace.c9.io/) for code editing
- [svg-pan-zoom](https://github.com/ariutta/svg-pan-zoom) for SVG interaction
- modl parser and SVG editing adapted from [curtcox/modl](https://github.com/curtcox/modl)
- Text outlines from Liberation Sans and DejaVu Sans Mono (see `src/text-outlines-LICENSE.txt`)

## License

BSD-3-Clause (see LICENSE-graphvizonline for GraphvizOnline attribution)
