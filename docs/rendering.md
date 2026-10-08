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

`AnimationGroup` and `LaggedStart` schedule independent child animations with
overlap, nesting, and optional timeline rescaling. The next child starts after
the previous duration multiplied by lag_ratio; the latest end determines the
natural duration. Group easing maps timeline time, while child easing maps local
progress. Completed animations hold terminal frames (or disappear for removers)
until final live-object cleanup. Each leaf snapshots its terminal state without
mutating the live scene early. Conflicting object families are rejected, as is
animating an individual child of a scene-added group. `VGroup` iteration permits
building child animation lists before adding those children independently.
`Succession`, repeated-object sequences, and automatic scene-family restructuring
remain unsupported.

`MoveAlongPath` centers an object on sampled path points while preserving its
orientation and style, with group scheduling and duration/easing overrides.
Paths are snapshotted at animation start. `point_from_proportion` applies the
same translation, scale, rotation, and geometry center as SVG rendering.
Circles and arcs use analytical circular motion; closed primitive outlines use
distance-weighted straight segments. Only XY Circle, Arc, Line, Polygon, Square,
Rectangle, and Triangle paths are supported. Arbitrary Bézier curves, text,
groups, arrows, 3D paths, live path updates, and automatic tangent orientation
remain unsupported. Zero-length segments are stable and nonfinite paths fail
explicitly.

`Arc` supports radius, start_angle, signed angle, arc_center, and ordinary shape
styles. SVG circular-arc commands are split at most half a turn per segment so
full turns render correctly. Local bounds include the sweep's extrema; rotated
bounds are conservative. The circular center is separate from the bounding-box
center used by normal transforms. `get_arc_center` and `move_arc_center_to`
respect geometry transforms; the latter also supports animate chains. Sweeps
are limited to one turn in the XY plane. Arc fill closes the chord, not a sector.
Multiple turns, num_components, sectors, and other Arc-specific APIs remain
unsupported.

`GrowFromCenter`, `GrowFromPoint`, and `ShrinkToCenter` sample uniform scaling
from an original geometry snapshot. External-point growth moves the center
linearly from the fixed point to its destination, preserving existing scale,
rotation, style, and group child coordinates. Center-based growth resolves its
pivot at playback start. Shrink leaves its live scale at zero and retains the
object by default; `remover=True` removes it at its local timeline end.
Group scheduling holds grown objects and
omits completed shrink removers without mutating live objects early. Only XY
point coordinates are supported; point_color, path_arc, and 3D growth are not.
Text centers remain anchors without browser font metrics.

Fill and stroke have separate color and opacity channels, including constructor
options and animated setters. `set_color` updates both colors; `set_fill` and
`set_stroke` affect only their channel. `set_opacity` sets both channel opacities
and can fill previously unfilled geometry. Setters recurse through children,
with `family=False` opting out. SVG group containers do not apply style-channel
opacity, avoiding repeated opacity multiplication in nested groups. Animation
fades still use container opacity as an independent multiplier. Arrow shaft
and head share stroke styling, and text supports outlines with default width
zero. Opacity is validated in [0, 1]; stroke width is finite/nonnegative.
Six-digit hex colors interpolate; other CSS color strings switch at completion.
Gradients, background strokes, and full Manim color parsing are unsupported.

`save_state` records a deep checkpoint without retaining prior checkpoints on
the same object. `restore` replaces live geometry/style state while keeping the
checkpoint available for reuse. `Restore` and `.animate.restore()` use existing
Transform sampling, including group timing, geometry interpolation, and
crossfades for different shape types. Transform completion preserves the source
checkpoint and does not adopt the target's checkpoint. Saved states are excluded
from recursive frame serialization. Root identity is retained; children are
copied on group restoration, matching the current group-transform behavior.
Camera state, scene membership, child identity preservation, and undo stacks
are outside this API. Construct Restore after saving the intended checkpoint;
the animation target is snapshotted at construction.

Next work can add additional verified compatibility APIs, geometry-aware path
transforms, glyph outline rendering, sequential animation composition, and an offline
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
Use `examples/staggered_scene.py` for delayed reveals and overlapping movement.
Use `examples/path_scene.py` for transformed circular/polygon paths and line motion.
Use `examples/arc_scene.py` for open paths, opposite sweeps, and transformed arc motion.
Use `examples/growth_scene.py` for point/center growth and staggered shrink cleanup.
Use `examples/style_scene.py` for distinct fill/stroke colors and animated group opacity.
Use `examples/restore_scene.py` for group restoration and recovery after shrinking.

## Verification

Check initial Pyodide loading, scene selection and URL reload, scale/rotation,
partial outline drawing, erasure, orbital motion, seeking/replay, source edits,
relative positioning and animated arrangements,
staggered starts and completed fades,
path motion and transformed path sampling,
syntax errors, missing scenes, and a runaway loop timeout. Ensure a new source
cannot select a scene class left behind by an older render. Check DOT rendering
and export after switching away from Manim. Run tests for timing and frame state
independently of browser integration; report both categories separately.

## References

- [Manim quickstart](https://docs.manim.community/en/stable/tutorials/quickstart.html)
- [Manim creation animation](https://docs.manim.community/en/stable/reference/manim.animation.creation.Create.html)
- [Manim rotation animation](https://docs.manim.community/en/stable/reference/manim.animation.rotation.Rotate.html)
- [Manim positioning methods](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)
- [Manim animation composition](https://docs.manim.community/en/stable/reference/manim.animation.composition.html)
- [Manim path movement](https://docs.manim.community/en/stable/reference/manim.animation.movement.MoveAlongPath.html)
- [Manim circular arcs](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.arc.Arc.html)
- [Manim growth from a point](https://docs.manim.community/en/stable/reference/manim.animation.growing.GrowFromPoint.html)
- [Manim shrinking](https://docs.manim.community/en/stable/reference/manim.animation.transform.ShrinkToCenter.html)
- [Manim vector styles](https://docs.manim.community/en/stable/reference/manim.mobject.types.vectorized_mobject.VMobject.html)
- [Manim restoration](https://docs.manim.community/en/stable/reference/manim.animation.transform.Restore.html)
- [Manim configuration](https://docs.manim.community/en/stable/guides/configuration.html)
- [Pyodide worker guidance](https://pyodide.org/en/stable/usage/webworker.html)

If full Manim Community rendering becomes a requirement, revisit runtime
feasibility. A server design must isolate arbitrary submitted Python, enforce
resource limits, disable unwanted host/network access, and clean up per-job
artifacts. Do not execute user scenes in a web server process.
