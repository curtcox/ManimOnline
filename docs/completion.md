# Completion evidence and remaining gates

The active request is to continue implementation until Manim support is fully
implemented. Current work is substantive progress, not proof of completion.
The documented architecture remains static browser execution. Whether the final
target is the existing MVP/version 1.0 roadmap or full Manim Community parity
has been asked of the user; do not silently equate the current subset with either.

## Roadmap acceptance audit (2026-10-08)

| Requirement | Current evidence | Remaining verification/work |
| --- | --- | --- |
| Basic shapes and animations | Python frame tests, SVG renderer tests, Pyodide browser playback | Browser compatibility matrix, broader examples |
| Worker execution and hard Python timeout | ManimClient deadline/cancellation tests; explicit cancel/retry controls; real in-app browser infinite-loop cancellation, 90-second timeout, valid-scene recovery and DOT switching | Repeat cancellation/timeout/recovery across browser matrix |
| Automatic detection and edit debounce | Literal/comment filtering, manual renderer selector with URL aliases, detector/scheduler tests, browser override/reload/recovery/gallery checks | Live sharing-service checks; broader ambiguous-source coverage |
| Scene selection and URL reload | Source-link snapshots, scene/type/DOT options, shortening failure/deadline/stale-response tests | Live shortening availability |
| Gallery | Bundled catalog, stale-load tests, browser loading | Preserve catalog acceptance as APIs change |
| MathTex | Python/backend/renderer tests, real formula SVG paths and export | Glyph bounds, substring APIs, tracing, broader formula coverage |
| SVG/PNG export for both renderers | Graphviz supports both; Manim exports current SVG or 800 × 450 PNG snapshot, with rasterization failure/cleanup tests | Browser export checks across supported browsers |
| Offline editing/rendering | Versioned complete asset cache, explicit update/retry UI, offline/partial-cache service worker tests | Real browser disconnected rendering and update/eviction behavior across browsers |
| Mobile-friendly UI | Stacked layout, wrapped code, larger controls, accessible toggle; browser checks at 390 × 844, 320 × 568, and desktop resizing | Native mobile keyboard/device coverage |
| Deployed site | Existing test and GitHub Pages workflows | Check every new commit's CI/deployment and deployed behavior |

Sequential and repeated-object animation now has Succession frame tests covering
stage starts, relative operations, replacement, removal, nested groups, checkpoints,
and terminal holds. Browser gallery playback verified accumulated rotation and
final removal, plus Graphviz after switching. Global numeric depth ordering now has Python/SVG tests and real Pyodide browser
checks across transformed groups, including animated crossings and restoration.
Root bring-to-front/back and clear/reintroduction now have Python tests and
Pyodide browser playback checks. Foreground APIs and broader family composition
remain implementation work. Scene lifecycle hooks and elapsed sampled time
have Python tests and Pyodide browser checks, including teardown animation.

Corner-path VMobjects now have Python/SVG tests and Pyodide checks for tracing,
movement, equal-count vertex interpolation, and cleanup. Unequal-count paths and
polygons crossfade; general geometry/path alignment remains open.

Full Community parity additionally requires general geometry/path morphing, full scene-family
composition and layering, camera configuration, glyph-level text/TeX
semantics, updaters, graphing, 3D, rendering/video output, and broad API/package
compatibility. These are not implemented or proven by the current tests. Keep
the original requested scope open until its requirements are clarified and
verified; successful individual feature commits do not close the overall goal.
