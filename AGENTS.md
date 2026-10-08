# Agent orientation

## Goal and current state

Build a browser experience for editing Manim source and previewing animations,
while preserving the existing Graphviz editor. This is a static GitHub Pages
site; the established direction is in-browser Pyodide and a limited Manim-lite
compatibility layer, not a server running full Manim Community.

## Read first

1. `README.md` for local serving instructions and public status.
2. `index.html` for editor setup, rendering integration, and output controls.
3. `src/manim-lite.py` for the compatibility API and timed frame generation.
4. `src/unified-worker.js` and `src/manim-client.js` for execution and deadlines.
5. `src/manim-renderer.js`, `src/manim-player.js`, and `src/detector.js`.
   `src/render-scheduler.js` coalesces editor/scene edits and cancels stale callbacks.
   `src/share-links.js` snapshots local share links and bounds optional shortening.
6. `docs/rendering.md` for current gaps and next milestones.
   `src/examples.js` contains the editor gallery catalog and stale-load protection.
   `src/manim-math.js` prepares vector formula glyphs for playback and SVG export.
   `src/manim-export.js` rasterizes current-frame PNG snapshots with bounded loading.
   `offline-assets.js`, `service-worker.js`, and `src/offline.js` manage offline files.
   Bump `OfflineAssets.VERSION` whenever a listed local asset changes, including
   `index.html`, runtime scripts, or gallery sources, to avoid serving old cached code.
7. `examples/multiple_scenes.py` for selection and geometry transform checks.
8. `examples/creation_and_rotation.py` for stroke creation and orbital motion.
9. `examples/layout_scene.py` for relative positioning and animated arrangements.
10. `examples/staggered_scene.py` for overlapping animation timing and cleanup.
11. `examples/path_scene.py` for transformed paths and center-following motion.
12. `examples/arc_scene.py` for open circular paths and signed sweeps.
13. `examples/growth_scene.py` for geometry growth and staggered shrink removal.
14. `examples/style_scene.py` for independent style channels and group opacity.
15. `examples/restore_scene.py` for checkpoint restoration and zero-size recovery.
16. `examples/indicate_scene.py` for temporary highlights and staggered emphasis.
17. `examples/copy_scene.py` for retained sources and independent target cleanup.
18. `examples/connector_scene.py` for transformed endpoint queries and animated connectors.
19. `examples/math_scene.py` for formula rendering and changed-formula crossfades.
20. `examples/succession_scene.py` for consecutive repeated-object animations and cleanup.
21. `examples/layer_scene.py` for global depth ordering across transformed groups.
22. `examples/order_scene.py` for root reordering, clearing, and reintroducing objects.
23. `examples/lifecycle_scene.py` for setup, teardown, and sampled scene time.
24. `examples/corner_path_scene.py` for straight-segment VMobject tracing and deformation.
25. `examples/foreground_scene.py` for grouped foreground overlays, release, and cleanup.
26. `examples/bezier_scene.py` for cubic tracing, parameter sampling, restoration, and mixed paths.
27. `examples/morph_scene.py` for unequal path alignment, restored pivots, and closing outlines.
28. `examples/shape_morph_scene.py` for primitive outline conversion and restored native geometry.
29. `todo/master_plan.md` and the other `todo/` documents for background plans.
    `docs/completion.md` tracks the remaining acceptance gates.

`ace/`, `viz-global.js`, and `svg-pan-zoom.min.js` are vendored dependencies.
Avoid editing these to implement Manim features. The Markdown files under
`examples/` illustrate the broader Manim API; they do not imply browser support.

Read `examples/group_morph_scene.py` for recursive family morphing, unequal child
counts, restoration, and removal. Alignment is snapshot-only; live children keep
existing completion/copy semantics.

Read `examples/group_family_scene.py` for indexing/slices, validated composition,
child removal/reordering, and whole-group animation. Group and VGroup share the
existing container serialization; slices share child identities but no parent
transforms. Do not bypass validated setters when adding family links.

Read `examples/camera_scene.py` for isolated config, square preview resolution,
per-frame backgrounds, and configured SVG/PNG export. Camera metadata is captured
with each frame; preserve default 800 × 450 behavior and per-source reset.

Read `examples/moving_camera_scene.py` for animated pan/zoom and saved-view
restoration. Camera frame roots participate in animation scheduling but are omitted
from display geometry; capture must use their sampled state, including held stages.

## Implementation guidance

- Keep the edit → render → preview loop central. Preserve DOT rendering, sharing,
  and exports when changing the unified flow.
- Extend the existing static architecture before introducing another stack.
  Full Manim, video encoding, LaTeX, and offline support are not proven here.
- Preserve the explicit Render animation/Cancel render controls and their stale-result guards.
- Keep Python execution in a worker so a main-thread timeout can terminate
  runaway code. A Promise timeout inside a blocked worker cannot interrupt it.
- Isolate each source execution namespace and ignore stale render results.
- Keep the compatibility layer in one source rather than divergent copies in
  the page and worker. Label supported behavior and unsupported features plainly.
- Use official Manim/Pyodide documentation when investigating compatibility.
- Keep generated media, caches, and temporary test output out of Git.
- Do not introduce accounts, sharing services, or server infrastructure unless
  the task calls for them. If a server is later introduced, submitted Python
  requires runtime isolation, resource limits, and per-job artifact storage.

## Verification and handoff

Run `python3 -m unittest discover -s tests -v` and `node --test tests/*.test.js`.
Serve locally with `python3 -m http.server 8000`. Check both a DOT graph and a
Manim example in a real browser. Syntax checks or native Python tests do not
prove Pyodide loading or browser playback. Report which checks actually ran.
Update the README and these notes when adding test commands or changing the
runtime. Do not claim full Manim compatibility from a subset implementation.

Read `examples/auto_zoom_scene.py` for combined camera fitting, single-object
focus and restoration. Margin adds to the chosen full frame dimension; preserve
inclusive visibility filtering, pre-mutation validation and deferred animation.
Framing uses existing geometry bounds; text glyph measurements remain open.

Read `examples/updater_scene.py` for timed callbacks, sampled-object following,
camera tracking, and callback cleanup. Keep callbacks out of frame JSON and expose
animation samples through original identities only for the update pass. Restore
live animated geometry in finally; preserve source callbacks during transforms.

Read `examples/value_tracker_scene.py` for shared animated values, callback ordering,
and consecutive relative increments. Trackers participate in timeline/updater
sampling but stay invisible in root and grouped rendering. Preserve finite real
validation and identity for in-place arithmetic.

Read `examples/redraw_scene.py` for factory-driven geometry, suspension/resumption,
and freezing callbacks. become must preserve source callbacks/checkpoints and
independent target geometry. Redraw copies update the callback argument; do not
capture a fixed original object in the regeneration callback.

Read `examples/numeric_scene.py` for DecimalNumber/Integer tracker labels,
formatted intermediate animation values and restoration. Numeric labels use
centered SVG Text, not native TeX digit families. Keep formatting options
independent of numeric interpolation and preserve atomic finite-value validation.

Read `examples/trace_scene.py` for TracedPath sampling, timed dissipation,
freezing and removal. Exclude traced_point_func from snapshots, preserve the
original sampled source identity, and bake current path transforms before
appending world-space points so earlier vertices retain their position.

Read `examples/ellipse_scene.py` for elliptical path motion, primitive morphing
and restoration. Ellipse dimensions are local geometry; preserve exact rotated
bounds, angular outline queries, and independent X/Y radii during cubic alignment.

Read `examples/sector_scene.py` for Sector/AnnularSector signed sweeps,
connected outline following and unequal-curve morphing. Preserve native inner-arc,
radial-edge, reversed-outer-arc and closing-edge order; zero inner radius is valid.
Sectors serialize through the existing bezierpath pipeline.

Read `examples/annulus_scene.py` for separate full-ring contours, outline motion,
radius interpolation and restoration. Preserve opposite winding and separate SVG
subpaths; never insert a radial connector. General disconnected morphing remains open.
