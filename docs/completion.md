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
Pyodide browser playback checks. Foreground root APIs now have ordering, release, removal, and atomic validation
tests and local Pyodide checks for promotion, release, transformed group painting,
and cleanup. Group/VGroup composition, indexing/slicing, and family queries now have atomic
validation and frame tests; general geometry-bearing families and scene
restructuring remain implementation work. Scene lifecycle hooks and elapsed sampled time
have Python tests and Pyodide browser checks, including teardown animation.

Corner-path VMobjects now have Python/SVG tests and Pyodide checks for tracing,
movement, vertex interpolation, and cleanup. Unequal connected path/polygon
counts now align through exact cubic subdivision, with tests and local Pyodide
checks for continuous morphing, restored pivots, and the final polygon; connected cubic paths support tracing, parameter sampling,
and equal-count control-point interpolation, with Python/SVG tests and local
Pyodide gallery checks. Primitive circle/ellipse/arc/sector/straight outlines now convert into
this morph pipeline, with Python tests and local Pyodide checks for primitive
transitions, restoration, and the terminal curve. Recursive ordered VGroup alignment now has frame tests for nested/unequal/empty
families, leaf wrapping, copy and sequential restoration. General Mobject family
restructuring remains open. Disconnected VMobject construction, separate SVG
contours and ordered per-contour alignment now support ring-to-outline morphs;
Annulus retains analytical radii for same-type transforms. Automatic contour
correspondence remains open. Raw get/set/append/clear points, subpath append and
copied outline append now have transformed-world-coordinate tests and animate
support. Full NumPy semantics, mutable points attributes and glyph geometry remain open.
Exact pointwise_become_partial/get_subcurve now support transformed geometry,
ordered disconnected contours, closed-outline wrapping and animated replacement.
ShowPassingFlash now travels over exact outline portions, including simultaneous
group highlights and reusable removed objects. Broader partial-creation APIs,
per-child passing-highlight delays and glyph geometry remain open.
RoundedRectangle now uses closed cubic outlines for circular/concave corners,
per-corner morphing, path following and restoration; general polygon rounding
and rectangle grids remain open.

NumberLine now supplies linear numeric conversion, ticks, numeric labels,
world-space extrapolation/projection and transform-aware marker updates. Python
checks cover transformed insertion without axis drift, sampling, validation,
length changes and restoration. Axes now combines two NumberLines, with Cartesian
conversion/inversion, batch coordinates, numeric and axis labels, transform-aware
updater geometry and atomic coordinate-label additions. Graphing still needs
NumberPlane, function plots and broader coordinate/graph APIs.

Full Community parity additionally requires general geometry/path morphing, full scene-family
composition and layering, 3D cameras and advanced camera APIs (2D settings, moving-camera pan/zoom and automatic bounds fitting now have Python/SVG tests), glyph-level text/TeX
semantics (basic DecimalNumber/Integer numeric labels now implemented), broader updater utilities (Mobject callbacks, real ValueTracker always_redraw and TracedPath now implemented), graphing, 3D, rendering/video output, and broad API/package
compatibility. These are not implemented or proven by the current tests. Keep
the original requested scope open until its requirements are clarified and
verified; successful individual feature commits do not close the overall goal.
