# Browser rendering direction

## Current architecture

ManimOnline is a static editor deployed through `.github/workflows/deploy.yml`.
`index.html` integrates ACE, DOT detection, Graphviz rendering, and a Pyodide
Manim-lite path. `src/manim-lite.py` implements a compatibility subset and generates timed frames.
`src/unified-worker.js` loads it into Pyodide; `src/manim-client.js` enforces the
90-second deadline and terminates active work on edits or Cancel render. The
Render animation control starts immediately and supports retry after failure.
Cancellation clears scheduled callbacks, advances the page revision, and discards
Python or formula results from the stopped render. Its controls remain available
through loading/execution/formula preparation and reset on completion or error.
The last completed preview remains paused during cancellation. A local in-app
browser check stopped an infinite-loop scene, retried it until the real 90-second
deadline, rendered a valid scene afterward, and then rendered a DOT graph. The worker rebuilds the
compatibility definitions and executes source in a fresh namespace per render.
`src/manim-renderer.js` turns serialized shapes into SVG and `src/manim-player.js`
provides playback, replay, and seeking. Preview generation is limited to 900 timed
samples plus a terminal frame (60 seconds at 15 fps), with a 12 MiB serialized
result limit. These bounds do not limit arbitrary Python memory allocation.

The established direction in `todo/master_plan.md` is in-browser execution and
frame playback. Full native Manim in WebAssembly has not been demonstrated.
Manim-lite is a compatibility subset, not the Manim Community engine.

## Depth ordering

Mobjects accept `z_index` and `set_z_index(value, family=True)`, including animated
changes. Values must be finite numbers; higher depths draw later. Family setters
recurse, while family=False affects only the selected object. Copy/checkpoint and
transform sampling retain depth. Renderer collection sorts drawable leaves
stably across group boundaries, reconstructing each leaf's ancestor transforms,
opacity, and creation progress. Equal depth keeps source scene/family order.
Group containers have no geometry and do not override their children's depth.
Foreground-object APIs and family restructuring remain unsupported.

Tests cover defaults/validation, recursive setters, animated crossings, copies,
checkpoints, global nested-group order, transforms/opacity, and stable ties.
Local Pyodide browser playback verified blue/yellow/red initial order,
blue/red/yellow order at three seconds, restored order at the end, and unchanged
group scale/translation. MathTex still produced vector paths, and DOT rendered
when switching afterward. See `examples/layer_scene.py`.

## Scene display controls

`bring_to_front` and `bring_to_back` reorder scene roots in argument order,
deduplicating repeated inputs and introducing absent objects. Whole groups retain
their geometry and identity; depth values are unchanged and still take priority.
`clear()` removes roots while keeping previous frames and reusable object state.
Nested family restructuring is explicitly rejected before any scene mutation.
These methods follow the [Scene display API](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html)
for supported roots; child restructuring is not implemented.

Python tests cover identity, ordering, new roots, empty calls, animation ties,
clear/reintroduction, checkpoints, invalid family operations, and gallery timing.
Local Pyodide browser checks verified the group's move forward before rotation,
move back afterward, blank frame at four seconds, and reintroduced title at the
end. DOT rendered after switching. See `examples/order_scene.py`.

## Scene lifecycle and clock

Scene rendering calls setup, construct, and tear_down in that order, then captures
the final state. Inherited hooks and hook-generated frames are supported. Errors
propagate and prevent later hooks from running. Read-only `Scene.time` counts
sampled frames from play/wait at 15 fps; clearing objects retains it. The terminal
still frame does not advance the clock. This is the preview timeline, independent
of loading/execution time and browser playback. Sub-frame durations round up.

Python tests cover inheritance, hook order, generated frames, failures, parallel
maximum duration, zero/sub-frame waits, rejected operations, and terminal time.
Local Pyodide playback showed setup-created title/shape, a 90-degree terminal
rotation, teardown's “Finished at 5.0s” text, and a seven-second full timeline.
DOT rendered after switching. See `examples/lifecycle_scene.py`.

## Corner paths

VMobject stores a connected list of finite XY corners, rendered as one SVG path.
Set/append corners, add_line_to, and reverse_direction support direct and animated
calls. Repeating the first corner closes the outline; empty paths render no
geometry. Endpoint queries and distance-based sampling apply the existing local
geometry transforms, with exact endpoints for straight-edged paths. Create and
Uncreate trace the whole connected stroke. Styles, checkpoints, depth/group
ordering, transforms, and MoveAlongPath use the existing pipeline. Same-count
vertex lists interpolate; different-count corner paths/polygons now align through
cubic subdivision as described below. Connected cubic handles are supported below; smoothing/multiple paths and
arbitrary shape alignment remain open.

Tests cover construction, extension, reversal, validation without partial edits,
empty/degenerate/closed paths, transformed endpoint queries, movement, tracing,
deformation, unequal-count alignment, checkpoints, SVG styles, and gallery
cleanup. Local Pyodide checks showed half tracing at one second, endpoint arrival
at five seconds, deformed vertices at six, removal at the end, and DOT after
switching. See `examples/corner_path_scene.py`.

## Implemented milestone and next work

The first animation slice implements creation/fades, timed transforms, animate
method chains, waits, play/pause, replay, seeking, and current-frame SVG/PNG download.
PNG snapshots pause playback and rasterize the serialized displayed frame at
800 × 450 on black. Image loading has a ten-second deadline; snapshot URLs are
released on success or failure, and changed-source results are discarded.

Offline preparation caches a versioned, exact manifest of the editor, gallery,
Pyodide core files, and pinned MathJax/LZString libraries. A complete install is
required before “Ready offline” appears. Updates wait for user reload or all old
tabs to close; failed installs preserve the previous version. Cache misses are
repaired online, with a recovery page for incomplete offline navigation. External
source URLs, arbitrary packages, and sharing-service responses are not cached.
Local-server shutdown/reload verified gallery MathTex and DOT rendering; full
internet-disconnection and cache-eviction checks across browsers remain open.

The Renderer selector supports Auto, Manim, and Graphviz. Overrides use the
existing `type` URL parameter and are preserved on reload and in links. Gallery
loading clears an override. Automatic detection strips quoted literals and
comments before scoring, avoiding language keywords inside scene text/labels.
`RenderScheduler` updates detection after 300 ms and starts rendering after
one second of quiet. Explicit rendering cancels both timers, and revision guards
discard callbacks already queued for superseded edits. Browser checks covered
manual selection/reload, forced-renderer errors, Auto recovery, literal filtering,
and gallery reset.

Share captures the latest source and relevant scene/renderer/DOT options in an
immediately copyable local link. Old source parameters are removed. Editing
invalidates the link and cancels pending optional shortening. `ShareClient`
bounds AllOrigins/is.gd requests and response reading to ten seconds, validates
the returned URL, and retains the source link on failure. Tests simulate service
success, failure, stalled bodies, cancellation, and stale results. Local browser
round trips restored RotatingSquare with its Manim override and neato/plain DOT
output; changing the scene cleared an outdated link. Live shortening-service
availability remains unverified.

At viewport widths up to 760 pixels, panels stack and code wraps; the toolbar
scrolls when needed and playback controls have larger touch targets. The code
toggle has labels and expanded state. Resize observers keep the editor and DOT
preview sized when the layout or editor visibility changes. Browser checks at
390 × 844 and 320 × 568 covered Manim playback/seek, hiding/restoring code,
DOT gallery switching, no horizontal page overflow, and desktop restoration.
This is viewport testing, not proof of native mobile keyboard/device behavior.
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
`Succession` prepares consecutive stages against an isolated copy of the scene,
applying each terminal state before preparing the next. Owned objects may repeat
between stages, while parallel conflicts still fail. Later introductions stay
hidden; replacement targets and removals are visible at the appropriate stage.
Live geometry/checkpoints remain untouched during preparation and final changes
commit in order. Nested groups/sequences and duration rescaling are tested.
Relative animate chains resolve at stage start; explicit Transform targets stay
construction-time snapshots. Root insertion order remains fixed during sampled frames; animated z_index values determine paint order
within a play call, and external read-only references do not follow simultaneous
animations. Only lag_ratio=1 is supported; family restructuring remains open.

`MoveAlongPath` centers an object on sampled path points while preserving its
orientation and style, with group scheduling and duration/easing overrides.
Paths are snapshotted at animation start. `point_from_proportion` applies the
same translation, scale, rotation, and geometry center as SVG rendering.
Circles and arcs use analytical circular motion; closed primitive outlines use
distance-weighted straight segments. Only XY Circle, Arc, Line, Polygon, Square,
Rectangle, Triangle, and VMobject corner/cubic paths are supported. Disconnected curves, text,
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

`Indicate` snapshots the current object at playback start and interpolates
toward a scaled, recolored snapshot. Its default there_and_back curve peaks at
halfway and returns to zero. Terminal frames always hold the exact original
state, and completion does not replace live objects or children or alter saved
checkpoints. Existing group scheduling supports independent staggered highlights.
Custom scale_factor/color and duration/easing are supported; factors must be
nonnegative and finite. Custom easing that ends away from zero jumps back when
the effect completes. The public there_and_back helper uses cubic smooth easing;
other transform animations still commit their target at completion. This is a
preview indication effect, not full Manim rate-function/transform semantics.

`TransformFromCopy` snapshots source and destination at playback start and
animates only the destination. It adds the destination once, preserves both live
objects and their child identities/checkpoints, and holds the destination after
completion in longer groups. Sources are read-only references and may animate
independently; add them explicitly to keep them visible. Matching geometry
interpolates, differing types crossfade, as with other transforms. Destination
family conflicts are rejected. This does not implement full Manim path morphing.

`Line` and `Arrow` expose transformed endpoints, vector, length, unit vector,
and angle through `get_start`, `get_end`, `get_start_and_end`, `get_vector`,
`get_length`, `get_unit_vector`, and `get_angle`. Endpoint editing via
`put_start_and_end_on` also works in animate chains. It preserves styles,
checkpoints, rotation, and nonzero scale; zero-scale lines recover using scale 1.
Ordinary endpoint animations interpolate both endpoints linearly with linear
easing. Recovery from zero scale follows the existing geometry interpolation.
Zero-length connectors have zero unit vector and angle. Coordinates must be
finite and in the XY plane. Queries refer to a child's coordinates within its
parent group; they do not accumulate parent transforms. Arrow queries use the
shaft endpoints, with the renderer's existing fixed local arrowhead. Buffers,
curved connectors, and attachment to object boundaries remain unsupported.

The editor's example picker loads supported Python scenes and a DOT diagram
from a fixed local catalog in `src/examples.js`. It resets scene selection and
URL source/type overrides, then uses the normal render and sharing pipeline.
Revision checks discard superseded responses and errors, including when edits
arrive during response-body loading. Failed loads leave editor source unchanged.
Toolbar controls wrap, with preview placement tracking the toolbar height.

`MathTex` serializes a formula and standard Mobject styles in the Python worker.
`src/manim-math.js` lazily loads MathJax 3.2.2 and compiles each distinct formula
once before playback, with stale-revision checks before/after asynchronous work.
The renderer copies inert vector geometry into each frame and centers the glyph
viewBox at the object anchor. Font cache is disabled, so exported SVGs contain
paths without external fonts or references. Formula changes crossfade; creation
and writing fade. Standard styles and group transforms apply to the formula.
TeX uses base and AMS packages, display math, a 1000 macro-expansion bound, and
a 4096-character buffer. Custom macros, links, external extensions, and native
LaTeX templates are unsupported. The loader has a 20-second connection deadline;
scenes are limited to 64 distinct formulas and 2 MiB of generated glyph SVG.
Python retains anchor-only bounds: substring objects, glyph tracing, glyph-aware
layout, `Tex`, and matching-symbol transformations need further implementation.
Math compilation currently runs in the browser DOM after worker execution;
the worker's 90-second Python deadline does not interrupt synchronous typesetting.

Next work can add additional verified compatibility APIs, geometry-aware path
transforms, glyph outline rendering, scene-family restructuring, and browser
compatibility verification. Keep DOT
rendering, sharing, and static SVG/PNG export working as these features evolve.

Use `examples/minimal_scene.py` as a baseline and `examples/multiple_scenes.py`
for scene selection with animated scale and rotation.
`examples/creation_and_rotation.py` demonstrates stroke creation, an orbit, and
erasure. Broader examples under `examples/`
are feature references, not an acceptance claim. Document unsupported APIs and
limits on duration/frame count. MP4 export, full LaTeX documents, 3D, arbitrary dependencies,
updaters, and offline caching remain future work unless separately implemented.
Use `examples/layout_scene.py` for shape spacing, dot positioning, and animated
row-to-column layout checks.
Use `examples/staggered_scene.py` for delayed reveals and overlapping movement.
Use `examples/path_scene.py` for transformed circular/polygon paths and line motion.
Use `examples/arc_scene.py` for open paths, opposite sweeps, and transformed arc motion.
Use `examples/growth_scene.py` for point/center growth and staggered shrink cleanup.
Use `examples/style_scene.py` for distinct fill/stroke colors and animated group opacity.
Use `examples/restore_scene.py` for group restoration and recovery after shrinking.
Use `examples/indicate_scene.py` for temporary size/color emphasis and staggered highlights.
Use `examples/copy_scene.py` for retained originals, crossfades, and target cleanup.
Use `examples/connector_scene.py` for endpoint motion and restored rotated arrows.
Use `examples/math_scene.py` for vector formulas, highlights, and formula crossfades.

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
- [Manim indication](https://docs.manim.community/en/stable/reference/manim.animation.indication.Indicate.html)
- [Manim copy transforms](https://docs.manim.community/en/stable/reference/manim.animation.transform.TransformFromCopy.html)
- [Manim line geometry](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.line.Line.html)
- [Manim MathTex](https://docs.manim.community/en/stable/reference/manim.mobject.text.tex_mobject.MathTex.html)
- [MathJax SVG output](https://docs.mathjax.org/en/v3.2/options/output/svg.html)
- [Manim configuration](https://docs.manim.community/en/stable/guides/configuration.html)
- [Pyodide worker guidance](https://pyodide.org/en/stable/usage/webworker.html)

If full Manim Community rendering becomes a requirement, revisit runtime
feasibility. A server design must isolate arbitrary submitted Python, enforce
resource limits, disable unwanted host/network access, and clean up per-job
artifacts. Do not execute user scenes in a web server process.

## Foreground roots

Scene add/remove_foreground_mobject(s) APIs maintain a separate foreground list.
Adding roots or preparing animations keeps foreground roots last for equal-depth
painting; numeric z_index still wins across all drawable leaves. Whole VGroups
retain their geometry transforms and opacity. Re-adding foreground roots reorders
that list. Releasing a designation keeps the root visible. Remove, FadeOut,
ReplacementTransform, and clear remove membership; bring_to_front preserves it
and bring_to_back releases it. Family restructuring is still explicitly rejected.
The grouped overlay gallery covers promotion, release, rotation, fade removal,
and clear/reintroduction. Python checks cover ordering, atomic rejection, cleanup,
and sequential animations; SVG depth sorting is shared with normal roots.

Local Pyodide browser checks confirmed the yellow grouped overlay paints after
the blue square, the released overlay paints before the red square, and promotion
restores its visibility during rotation. The clear interval is empty and the
terminal frame contains only the title. DOT rendered after switching.

## Connected cubic curves

CubicBezier and VMobject.add_cubic_bezier_curve_to now serialize connected
four-control-point segments as SVG cubic commands. Corner paths remain unchanged
until a cubic append converts their straight segments. Subsequent corners append
straight cubics; replacement/reversal and animated operations preserve the API.
Sampling partitions by approximate curve lengths (20 intervals) and uses each
curve's parameter, with exact endpoints. Bounds enclose control points. Matching
curve counts interpolate; unequal connected paths align through subdivision. General alignment,
disconnected subpaths, smoothing, and full point-array APIs remain gaps.

Python/SVG tests cover finite XY validation, exact transformed endpoints, cubic
midpoints, mixed segment allocation, reversal, matching/unequal-count transforms,
restoration, tracing, styles, and the gallery. Local Pyodide checks verified
half-stroke tracing, endpoint arrival, intermediate control-point deformation,
restoration, and the final mixed path. DOT rendered after switching.

## Unequal connected-path alignment

Transform snapshots convert corner/polygon edges to cubics and subdivide the
shorter curve list evenly to match counts. Exact De Casteljau splitting retains
curve geometry and existing joins; stored geometry pivots preserve transformed
endpoint frames even when control-point bounds change. Matching anchors/handles
interpolate in one drawable path, including corner-to-cubic and open-to-closed
morphs. Closed SVG paths use Z to retain stroke joins. Live geometry and target
identity are unchanged until normal completion; checkpoints restore original
representations. Empty paths still crossfade. No automatic winding/correspondence,
disconnected subpaths, primitive conversion, or family alignment is implied.

Python checks verify subdivision at several parameters, preservation of joins and
transformed pivots, immutable source/target snapshots, singleton/empty geometry,
copy/replacement/restoration, and sequential stages. SVG tests verify closed joins.
Local Pyodide playback showed one fully opaque path at the unequal-count midpoint,
a restored rotated/scaled curve, and the final polygon. DOT rendered after switching.
