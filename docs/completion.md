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
| Worker execution and hard Python timeout | ManimClient deadline/cancellation tests | Recheck real runaway Python and recovery across browsers |
| Automatic detection and edit debounce | Existing detector and unified rendering code, browser switching | Dedicated detector/debounce coverage and manual override UI |
| Scene selection and URL reload | Browser selection/reload checks | Full sharing-service success/failure checks |
| Gallery | Bundled catalog, stale-load tests, browser loading | Preserve catalog acceptance as APIs change |
| MathTex | Python/backend/renderer tests, real formula SVG paths and export | Glyph bounds, substring APIs, tracing, broader formula coverage |
| SVG/PNG export for both renderers | Graphviz supports both; Manim exports current SVG frame | Implement and verify current Manim frame PNG export |
| Offline editing/rendering | No service worker implemented | Cache/version strategy, assets, offline/partial-cache tests |
| Mobile-friendly UI | Wrapped toolbar and dynamic preview placement | Responsive editor/preview and mobile browser tests |
| Deployed site | Existing test and GitHub Pages workflows | Check every new commit's CI/deployment and deployed behavior |

Full Community parity additionally requires geometry/path morphing, sequential
and repeated-object animation, camera configuration, glyph-level text/TeX
semantics, updaters, graphing, 3D, rendering/video output, and broad API/package
compatibility. These are not implemented or proven by the current tests. Keep
the original requested scope open until its requirements are clarified and
verified; successful individual feature commits do not close the overall goal.
