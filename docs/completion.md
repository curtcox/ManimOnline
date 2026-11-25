# Completion and acceptance

This page records what is verified and what remains open. Manim-lite is a large
compatibility subset of Manim Community 0.22, not the Community engine; passing the gates
below does not mean full Community parity. Supported features and known gaps are listed in
[rendering support and limitations](rendering.md).

## Acceptance gates

| Area | Evidence | Still open |
| --- | --- | --- |
| Manim rendering and playback | Python frame tests; renderer, player and 3D projection tests; browser smoke renders DOT, Manim, MathTex, NumPy, 3D and raster scenes with exported-pixel checks in Chromium, Firefox and WebKit (CI) | Real Safari and Firefox releases rather than Playwright builds |
| Worker isolation and deadlines | Client deadline and cancellation tests; opaque-sandbox check in `tests/browser/smoke.cjs` | Cancellation and timeout recovery across the whole browser matrix |
| Three languages and detection | Detector tests; `tests/browser/languages.cjs` renders Graphviz, modl and Manim | Broader ambiguous-source coverage |
| Links, drafts and HashBin | Share-link, draft and HashBin unit tests; `languages.cjs`, `legacy-publish.cjs` and `url-state.cjs` with a mocked HashBin service; shortening failures in `sharing.cjs` | Live HashBin Publish save and reload on the production origin; live shortening-service availability |
| Gallery | `gallery.cjs` checks every cover, MP4 playback, filters, editor loads in all three languages, stale loads and the phone layout; `npm run check` fails on stale previews | — |
| Formulas | MathJax and Typst unit tests; browser measurement pass; `cold-math.cjs` verifies cross-origin math scripts before caching | Exact Computer Modern formula outlines |
| Export | SVG/PNG export tests; MP4/WebM container and pipeline tests; Chromium decode, duration and seeking checks | Safari and Firefox encoder coverage; audio tracks |
| Offline | Offline unit tests; `upgrade.cjs` covers a returning visitor's cached editor, activation, source preservation and offline covers | Disconnected rendering and storage eviction in real browsers |
| Phones | Phone layout, sample-video-first loading and touch pan/zoom (`touch.cjs`, Chromium only) | Native device and keyboard testing |
| Optional AI | `ai.test.js` and `tests/browser/ai.mjs` with mocked providers | Live provider runs; quality is not measured by the bundled suite |
| Deployment | CI runs the shared Fragment Kit gates and all browser suites before `deploy.yml` publishes | Check each deployment's behavior on the production origin |

## Current test totals

Measured 2026-11-25 on `main`: 170 Node tests and 754 Python tests pass (one Python test
skips when Pygments is not installed).

## Community parity measurements

These differential runs compare Manim-lite with a Manim Community 0.22 install (TinyTeX for
LaTeX, Liberation Sans registered for text) on per-frame bounds, family structure and
durations. They are bounds-level comparisons, not pixel comparisons, and were last
measured in October 2026.

| Corpus | Result |
| --- | --- |
| Community `.. manim::` docstring examples (414) | 406 render; the other 8 also fail in Community. Frame bounds match for 289 of 375 comparable examples; remaining differences are formula estimates in native runs (no browser measurement), harness artifacts and fonts other than Liberation Sans |
| Community documentation gallery, tutorial and guide examples (75) | All render |
| Community's own module tests (`tests/module`, 655) | 573 pass; failures are private internals, file-system TeX/Typst output, OpenGL, intentional rounding differences and the fixed 15 fps |
| Random animation-chain fuzz suites | 1,780 of 1,782 scenes match |
| Text-focused fuzz suite (120 scenes) | All match |
| Browser (Pyodide, Chromium) | Every `examples/` gallery scene renders without page errors and also runs in Community |

Harness locations and commands for these corpora are recorded for maintainers outside the
repository; see the parity notes in [AGENTS.md](../AGENTS.md).

## Open work

- The gaps listed under **Known gaps** in [rendering](rendering.md).
- Live production checks: HashBin Publish save/reload, shortening services and
  deployment behavior.
- Broader real-browser coverage: Safari and Firefox releases, native phones, offline
  disconnection and eviction.
