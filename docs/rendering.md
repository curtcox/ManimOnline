# Browser rendering direction

## Current architecture

ManimOnline is a static editor deployed through `.github/workflows/deploy.yml`.
`index.html` integrates ACE, DOT detection, Graphviz rendering, and a Pyodide
Manim-lite path. `src/manim-lite.py` implements a compatibility subset and generates timed frames.
`src/unified-worker.js` loads it into Pyodide; `src/manim-client.js` enforces the
90-second deadline and terminates active work on edits. The worker rebuilds the
compatibility definitions and executes source in a fresh namespace per render.
`src/manim-renderer.js` turns serialized shapes into SVG and `src/manim-player.js`
provides playback, replay, and seeking. Preview generation is limited to 900 timed
samples plus a terminal frame (60 seconds at 15 fps), with a 12 MiB serialized
result limit. These bounds do not limit arbitrary Python memory allocation.

The established direction in `todo/master_plan.md` is in-browser execution and
frame playback. Full native Manim in WebAssembly has not been demonstrated.
Manim-lite is a compatibility subset, not the Manim Community engine.

## Implemented milestone and next work

The first animation slice implements creation/fades, timed transforms, animate
method chains, waits, play/pause, replay, seeking, and current-frame SVG download.
Creation traces normalized SVG outlines and fades in their fill. Uncreate
reverses drawing and removes the object. Group children and arrow components
reveal simultaneously; text creation and writing use fades. Transforms between
different shape types crossfade.
Tracing uses scaling strokes for accurate path fractions at any preview size;
completed objects return to non-scaling strokes.
The Scene field selects a source-defined class and defaults to the first one.
Successful renders return scene names for suggestions, and URL/shared links
preserve selection with the `scene` query parameter. Missing selections fail
explicitly; no class from previous source is used.

Uniform scale and 2D rotation are serialized as SVG transforms around geometry
centers. They support direct calls and animation chains, with explicit external
pivots. Group centers use child bounds, and text uses its anchor without full
font metrics. External-pivot animations interpolate center positions between
endpoints. `Rotate` and `Rotating` instead sample rigid rotations from the
original state at each frame and preserve orbital radius around an explicit
pivot. Only the XY plane with OUT/IN axes is supported. Full Manim semantics
are not implied.

Layout supports `next_to` with a bounding-box gap and aligned edge, and
`VGroup.arrange` with direction, buffer, and optional centering. `move_to` uses
the geometry center and accepts a point or another object. `Dot` uses a filled
circle with radius 0.08 and no outline. Layout and arrangement also work in
animate chains. Arrange groups before applying group scale/rotation; rearranging
an already scaled or rotated group is explicitly unsupported. Child coordinates
are local to their group. Bounds do not include text metrics, arrowheads, or
stroke thickness; rotated polygon/line bounds are conservative.

Next work can add additional verified compatibility APIs, geometry-aware path
transforms, glyph outline rendering, staggered animation timing, and an offline
asset strategy. Keep DOT
rendering, sharing, and static SVG/PNG export working as these features evolve.

Use `examples/minimal_scene.py` as a baseline and `examples/multiple_scenes.py`
for scene selection with animated scale and rotation.
`examples/creation_and_rotation.py` demonstrates stroke creation, an orbit, and
erasure. Broader examples under `examples/`
are feature references, not an acceptance claim. Document unsupported APIs and
limits on duration/frame count. MP4 export, LaTeX, 3D, arbitrary dependencies,
updaters, and offline caching remain future work unless separately implemented.
Use `examples/layout_scene.py` for shape spacing, dot positioning, and animated
row-to-column layout checks.

## Verification

Check initial Pyodide loading, scene selection and URL reload, scale/rotation,
partial outline drawing, erasure, orbital motion, seeking/replay, source edits,
relative positioning and animated arrangements,
syntax errors, missing scenes, and a runaway loop timeout. Ensure a new source
cannot select a scene class left behind by an older render. Check DOT rendering
and export after switching away from Manim. Run tests for timing and frame state
independently of browser integration; report both categories separately.

## References

- [Manim quickstart](https://docs.manim.community/en/stable/tutorials/quickstart.html)
- [Manim creation animation](https://docs.manim.community/en/stable/reference/manim.animation.creation.Create.html)
- [Manim rotation animation](https://docs.manim.community/en/stable/reference/manim.animation.rotation.Rotate.html)
- [Manim positioning methods](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)
- [Manim configuration](https://docs.manim.community/en/stable/guides/configuration.html)
- [Pyodide worker guidance](https://pyodide.org/en/stable/usage/webworker.html)

If full Manim Community rendering becomes a requirement, revisit runtime
feasibility. A server design must isolate arbitrary submitted Python, enforce
resource limits, disable unwanted host/network access, and clean up per-job
artifacts. Do not execute user scenes in a web server process.
