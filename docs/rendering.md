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
cubic subdivision as described below. Connected cubic handles, separate contours and smoothing are supported below;
arbitrary shape alignment remains open.

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
supported outlines use cubic alignment; other shape-type pairs crossfade.
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
animate chains. Rearranging scaled/rotated groups now supports nonzero signed
scales, as described in the transformed-layout section below. Child coordinates
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
outline morphing and crossfades for unsupported combinations. Transform completion preserves the source
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
interpolates, supported outlines morph, and unsupported types crossfade. Destination
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
parent group; they do not accumulate parent transforms. Arrow logical endpoint
queries include tip points; own points describe the trimmed shaft. Buffers and
straight tip attachment are supported. CurvedArrow/CurvedDoubleArrow support is described below. Attachment to
object boundaries remains unsupported.

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
full point-array semantics remain gaps. Separate contours and smoothing are described below.

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
family alignment is implied by this connected-path milestone. Separate contours
are now described below. Primitive conversion is
now described below.

Python checks verify subdivision at several parameters, preservation of joins and
transformed pivots, immutable source/target snapshots, singleton/empty geometry,
copy/replacement/restoration, and sequential stages. SVG tests verify closed joins.
Local Pyodide playback showed one fully opaque path at the unequal-count midpoint,
a restored rotated/scaled curve, and the final polygon. DOT rendered after switching.

## Primitive outline conversion

Cross-type Transform/Restore/copy/replacement frames convert Circle, Arc, Square,
Rectangle, Triangle, and Line to the connected cubic alignment pipeline. Matching
primitive types keep native parameter interpolation. Straight edges are exact;
circular segments span at most 45 degrees and use tangent handles, with exact
end anchors and full-turn closure. This introduces a small circular approximation
only during cross-type morphing. Tests densely sample the radial error below
0.0005% of radius, verify tangent direction and signed/zero/full sweeps, preserve
original pivots, and check native completion/restoration. Arrowhead, text/glyph,
and full group-family outline matching remain gaps.

Local Pyodide playback verified a single opaque, closed eight-segment outline
at the circle/square midpoint, the triangle transition, restored circle scaling,
and the terminal open cubic. DOT rendered after switching.


## Recursive group transforms

VGroup Transform/Restore/copy/replacement sampling aligns nested child snapshots
recursively. Children match by order. Smaller nonempty families expand with evenly
distributed transparent duplicates, following the ordered-repeat strategy in the
[Manim alignment source](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).
Empty families use transparent, zero-scale copies of their counterpart children.
Leaf-to-group transitions wrap the leaf in a neutral container. Each matched leaf
uses the existing outline interpolation or unsupported-type crossfade. Parent
position/rotation/scale, opacity, depth and original pivots interpolate separately.
Alignment caches are rebuilt at each animation start, including Succession stages;
original source/target objects remain untouched until normal completion.

This extends geometry alignment, not scene-family restructuring or child identity
preservation. Unsupported glyph/arrow pairs still crossfade at their leaf level;
automatic matching remains open; separate contours are described below. The group-morph gallery
covers nested unequal families, checkpoints, and group erasure.

Local Pyodide browser checks showed four continuously morphed paths at three
seconds, with full opacity on original children and half opacity on the two
inserted duplicates. At eight seconds the blue circle and yellow square were
restored; the terminal frame retained only the title. DOT rendered after switching.


## Group composition and selection

Group and VGroup use the existing container renderer and permit the runtime's
supported geometry/text children. Constructors, add, add_to_back, and submobjects
assignment validate all inputs and reject cycles before mutation. Duplicate
children are ignored. Re-add moves a child to the end, while add_to_back places
selected children first. Remove affects only immediate children. Indexing, negative
indices, slices, iteration, len and split expose immediate children. A slice is a
neutral Group/VGroup referencing the same objects, without parent transforms;
copy remains deep and retains shared aliases within the copied family. get_family
returns stable, deduplicated descendants including self. These behaviors follow
the [Manim family API](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html)
for supported containers. VGroup currently also accepts the supported text classes.

Python checks cover validation without partial edits, direct/indirect cycles,
deduplication, reordering/removal, shared slice styling, empty/reversed slices,
family traversal, independent copies, and preserved previous frames. The family
gallery edits a scene-added group and then rotates/removes it as a whole. Individual
child animation within a scene-added group remains explicitly rejected. Generic
geometry-bearing Mobject child composition and automatic scene restructuring
still need implementation. Mutating the returned list directly bypasses validation;
use group methods or the submobjects setter to change family links.

Local Pyodide checks verified yellow circle/triangle with an unchanged red square
at one second, two children after removal at two seconds, red-square-first order
with 90-degree parent rotation at five seconds, and no shapes after fade removal.
The DOT gallery rendered correctly after switching.


## 2D canvas configuration

Global config exposes pixel_width, pixel_height, frame_height, frame_width, and
background_color through attribute/dict access. It resets for each source execution
and is restored after success or failure. Scene snapshots config at construction
with optional camera_config overrides; self.camera supports the same properties.
Pixel dimensions are integers 1–4096; frame sizes are positive finite units;
background accepts six-digit hex strings. Frame width follows pixel aspect ratio,
and setting width adjusts height. Defaults deliberately preserve the existing
800 × 450, 16 × 9 preview rather than claiming native Manim defaults.

Camera metadata is captured per frame. The renderer scales its internal geometry
coordinates to the frame extent and output resolution, preserving shape proportions
for consistent aspect ratios. Explicit background rectangles survive SVG export;
PNG uses displayed SVG dimensions. The canvas gallery uses a 600 × 600 white
background and changes it during the timeline. Frame rate, moving-camera animations,
3D, config files and general ManimConfig semantics remain gaps. See the
[official configuration guide](https://docs.manim.community/en/stable/guides/configuration.html)
for the full API. Python/SVG tests cover settings, bounds/validation, frame snapshots,
failed/successful-source isolation, aspect ratio, defaults and background geometry.

Local Pyodide checks confirmed 600 × 600 SVG dimensions and a 1.5 camera scale,
with the terminal pale background. A real PNG download was decoded as 600 × 600
RGBA with corner pixel (232, 238, 247, 255), matching #E8EEF7. Loading the baseline
scene restored 800 × 450 black output, and DOT rendered after switching.


## Moving camera frames

MovingCameraScene adds self.camera.frame, a positive axis-aligned rectangle with
Mobject pan/zoom and checkpoints. Move/shift/scale and width/height setters work
in animate chains, using the existing timeline, easing, parallel holds and
Succession preparation. Camera frames may enter the internal scene root list for
animation preparation but are omitted from drawable snapshots. Capture reads
the camera frame override directly, preserving immutable earlier frames. Clearing
drawable objects does not reset the camera view. The renderer applies inverse
center translation after view scaling; scene geometry/queries keep world positions.
Background and configured export dimensions remain independent of focus.

The API follows the basic frame usage in the
[MovingCameraScene documentation](https://docs.manim.community/en/stable/reference/manim.scene.moving_camera_scene.MovingCameraScene.html).
Rotation, 3D, frame replacement/removal effects
and full camera APIs remain unsupported. Camera frames cannot belong to display
groups. Python tests cover intermediate pan/zoom, checkpoints, consecutive
relative stages, parallel completion holds, clear persistence, camera overrides,
setters and invalid state. SVG tests cover focus inversion without object mutation.

Local Pyodide playback verified a 2× view focused on x=2 at four seconds, a 2×
view focused on x=-2 at six seconds, and the exact default view at the end. The
scene showed only its original square/circle/title, with no camera rectangle.
DOT rendered after switching.


## Automatic camera framing

MovingCamera.auto_zoom accepts one Mobject or an iterable, selects the limiting
width/height relative to the current view, adds margin to that full dimension,
and centers the frame on combined bounds. It returns a deferred animation by
default or updates immediately with animate=False. Frame objects are ignored;
only_mobjects_in_frame filters by inclusive bounding-box overlap using is_in_frame.
frame_center also supports direct read/write. These follow the
[official camera implementation](https://docs.manim.community/en/stable/_modules/manim/camera/moving_camera.html).
Validation precedes mutation; empty selections, invalid bounds, non-XY geometry,
and nonpositive fitted dimensions fail explicitly. Negative margins can crop when
the final dimension stays positive. Existing transformed geometry bounds are
conservative for curves/groups; glyph measurement remains open. The fit is computed
when auto_zoom is called, rather than continuously tracking later object changes.
Tests cover width/height fits, deferred sampling, transformed groups, edge overlap,
filtering, generators, invalid-input atomicity and restored checkpoints.

Local Pyodide playback verified the combined fit at four seconds (8-unit width,
2× zoom), single-circle focus at seven seconds (3-unit height, 3× zoom, x=-2),
and the exact original view at nine seconds. DOT rendered after switching.


## Mobject updaters

Mobject callback management and recursive update/suspend/resume follow the
[official updater API](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).
A callback takes the object, optionally with a parameter named dt. Each timed
operation starts with dt=0, advances at 15 fps and updates the exact terminal state.
Shared family members update once in stable scene order. Camera frames join this
update pass even when absent from drawable roots. Animation-owned families are
suspended for the sampled operation; dependent callbacks see temporary sampled
geometry through the original object identities. Geometry is restored in finally,
including callback failure. Snapshots keep their original morph pivots. Crossfades
expose their more visible snapshot to queries. Transform completion/checkpoint
restoration preserve source callback registrations. Callbacks/suspension/private
sample state never enter JSON. Frozen earlier frames remain immutable.

Scene callbacks, custom UpdateFromFunc animations,
and changing scene membership/family structure during callback execution still
need implementation. Group children retain the existing local coordinate query
semantics. Tests cover waits, time totals, following sampled movement, camera
tracking, suspension, callback order/removal, shared-family deduplication, failure
cleanup, checkpoint/transform retention, and gallery terminal geometry.

Local Pyodide gallery playback verified a centered camera at the three-second
midpoint and a final x=2 focus. The follower ended at (2,1), while the independent
spinner stopped at 450 degrees after callback removal. DOT rendered after switching.


## Animated real parameters

ValueTracker implements finite real get/set/increment and the scalar arithmetic
operators, preserving identity for in-place operations. Its x coordinate encodes
the parameter, following the [official ValueTracker API](https://docs.manim.community/en/stable/_modules/manim/mobject/value_tracker.html).
Animate set/increment, Transform/Restore, easing and sequential stages interpolate
through existing snapshots; updater exposure makes sampled values available to
original callback references. Root trackers are omitted from drawable frames;
renderer handling also omits trackers nested in a Group. Scene-added trackers can
run timed callbacks, ordered before later dependents. Copy/checkpoints remain
independent. Complex values, point arrays and glyph-level numeric text semantics remain open.
Tests cover arithmetic/validation without partial updates, hidden output, timed
callbacks, copy/restoration, relative succession and connector endpoints.

Local Pyodide playback verified value=1 at three seconds: dot at (1,-1), square
at (-1,1), and matching connector endpoints. Consecutive decrements ended with
both shapes on x=0 at seven seconds, with exactly three visible shapes. DOT
rendered after switching.


## Geometry regeneration

Mobject.become replaces supported geometry/style state while retaining root identity,
callbacks, suspension and checkpoints. Targets are copied before replacement;
ordered existing child links are reused, new children are copied, excess children
are removed, and shared target aliases are retained. Source aliases split when
separate target children require independent geometry. Python classes stay unchanged;
use generic Mobject queries for cross-type replacement. Camera/tracker roots only
accept their own kind, and camera geometry is validated before mutation.

always_redraw attaches a callback that calls become(factory()) each update, following
the [official continuous-update utility](https://docs.manim.community/en/stable/_modules/manim/animation/updaters/mobject_update_utils.html).
The callback acts on its argument so deep copies regenerate themselves. Root callback
registrations stay intact across regeneration, even if the factory returns fresh
objects each time. Factories execute in Python and see exposed animation samples.
Suspension and callback removal freeze geometry; invalid factory results preserve
the last valid object and fail the render. Native become fitting/stretch parameters,
full family identity alignment and scene restructuring remain open. Tests cover
copy isolation, checkpoint/callback retention, child links/aliases, sampled dimensions,
suspension/freezing, factory errors, immutable earlier frames and gallery playback.

Local Pyodide gallery playback verified the suspended circle stays at radius 1.5
at four seconds while the group continues shrinking. After resumption the circle
ends at radius 1, and the group's square stays frozen at side .5 after callback
removal. SVG dimensions were 75/50 pixels at four seconds and 50/25 at the end.
DOT rendered after switching.


## Numeric text labels

DecimalNumber and Integer render finite real values as existing SVG text. Their
get/set/increment methods follow the [official numeric API](https://docs.manim.community/en/stable/_modules/manim/mobject/text/numbers.html)
for fixed precision, signs, comma grouping, ellipsis and plain unit suffixes.
Integer defaults to zero decimal places and rounds its getter. Negative rounded
zero suppresses the minus sign. Precision is bounded to 0–12 and unit strings to
256 characters; invalid values fail before changing an existing label.

Numeric snapshots interpolate the real value and regenerate formatted text,
keeping formatting settings discrete. Direct animate, relative Succession and
Restore therefore show intermediate numbers. Tracker-driven callbacks update
labels at sampled positions while preserving styling and earlier frame snapshots.
Labels can become plain Text or other supported geometry without stale numeric
serialization. Tests cover formatting, integer ties, validation, copy/checkpoints,
intermediate values, restoration, source replacement and the gallery.

Text remains centered with browser font metrics. Native digit families, edge_to_fix,
glyph bounds/indexing, complex values, TeX units and Variable remain open.

Local Pyodide gallery playback verified +1.00 and 1 at three seconds, the direct
numeric animation at 1,750 points after five seconds, and restoration to 1,000
points at the end. Graphviz rendered after switching.


## Point tracing

TracedPath uses Mobject updaters to connect finite XY points through the existing
VMobject polyline representation. It follows animation sample exposure and source
callback order. The [official TracedPath source](https://docs.manim.community/en/stable/_modules/manim/animation/changing.html)
adds a straight segment per update and, after dissipating_time, removes one old
segment per update. The preview follows that frame-based retention rule rather
than time-clipping individual segments. None/zero disables dissipation; negative
or nonfinite durations fail early. Pauses and callback removal preserve geometry.

Transforms are baked into existing vertices before adding a new world-space point,
preventing changing bounds from moving a rotated trail's pivot. Copy callbacks
operate on the copied trace. As for other callbacks, function closures retain their
captured references; copied bound point methods follow Python deepcopy behavior.
The point provider is excluded from JSON. Invalid samples leave existing geometry
and the dissipation clock unchanged. Tests cover sampled animation endpoints,
source ordering, immutable old frames, dissipation, suspension, copies/checkpoints,
transformed vertices, invalid points and gallery removal. 3D trails, smooth
reconstruction and stroke-opacity gradients remain open.

Local Pyodide gallery playback verified a three-quarter blue trail and a short
yellow trail at three seconds. By 5.9 seconds the blue circle stayed frozen and
the yellow path contained only coincident endpoint samples. All geometry was
removed at seven seconds; DOT rendered after switching.


## Elliptical geometry

Ellipse follows the [official width/height constructor](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html)
with defaults 2×1. It renders as SVG ellipse with separate X/Y radii. Finite
nonnegative dimensions include collapsed geometry; invalid values fail during
construction. Existing style, transform, creation/growth and checkpoint pipelines
apply. Local bounds use half dimensions; rotated world bounds use exact elliptical
extents instead of rotated rectangle corners. Outline queries use angular
proportion, matching the current Circle approach rather than constant speed.

Eight cubic arc segments with separately scaled coordinates join the existing
primitive morph alignment pipeline, preserving original pivots and terminal
ellipse metadata. Tests cover defaults/validation, degenerate dimensions, rotated
bounds and path points, cubic alignment, morph/restoration gallery frames, SVG
radii, styles, creation dashes and transforms. Native stretch methods and general
point-array operations remain open.

Local Pyodide playback verified the 30-degree ellipse with SVG radii 100/50 pixels,
the dot at (-.5, .866) after two seconds, a single cubic morph outline at six
seconds, and the restored ellipse without the dot at ten seconds. DOT rendered
after switching.


## Circular sectors

Sector and AnnularSector use the [official connected contour order](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html):
inner arc, radial connector, reversed outer arc, closing connector. Sector fixes
the inner radius to zero. Constructor defaults match the native radius/sweep/style
options; signed sweeps are bounded to one full turn as for Arc. Radii must be
finite and nonnegative, including zero/equal/reversed radii. Arc centers support
finite XY coordinates. Both classes participate in Arc/VMobject queries and
serialize to the existing connected cubic path backend, retaining source sector
metadata across checkpoints and restoration.

Existing SVG path creation, fill/stroke, scaling/rotation, outline motion, growth
and unequal-curve alignment apply without a separate rendering representation.
Bounds conservatively include cubic control points; path-distance queries use
existing sampled cubic lengths. No disconnected full Annulus API is implied.
Tests cover defaults, closed contour order, signed angles, validation, transformed
arc centers, path queries, unequal morphing, restored metadata and gallery output.

Local Pyodide gallery playback verified a filled quarter wedge and clockwise
three-quarter ring sector with an empty center. At six seconds the ring morph
used fourteen cubic segments; restoration retained two closed sector paths at
ten seconds without the follower dot. Graphviz rendered after switching.


## Complete rings

Annulus follows the [official outer-circle/reversed-inner-circle topology](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html).
Its snapshot stores two radii and a center, and the SVG backend emits separately
closed, oppositely wound arc contours. Nonzero fill preserves the hole and no
radial segment is stroked. Defaults and validated radius/XY/style options parallel
Sector; equal, zero and reversed radii are stable. mark_paths_closed is accepted
but contours are always closed for browser rendering.

Exact radial bounds include the larger radius. Path queries traverse outer then
inner contours with separate start/end points, weighted by circumference; motion
jumps between subpaths. Same-type transforms interpolate radii analytically;
copy/checkpoints, creation, growth and restoration use the existing pipeline.
Other supported outlines now use separate-contour alignment described below. Tests cover
validation, degenerate endpoints, transformed bounds, contour order, intermediate
radii, gallery restoration, opposite SVG winding, no radial stroke and tracing.

Local Pyodide playback verified separate closed contours at two seconds with
an empty center and no radial seam. At seven seconds the radii interpolated to
0.95 and 1.75; the eleven-second final frame restored 0.7 and 1.5 and removed
the follower dot. Graphviz rendered after switching examples.

## Rounded rectangles

RoundedRectangle uses the [official corner-cut and radius ordering](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/polygram.html).
It accepts finite scalar or repeating per-corner radii, including negative values
for concave cuts, and finite nonnegative width/height. Cuts clamp to half the
shorter side. The native radius sequence starts at upper-left; the closed path
starts at upper-right. Four two-cubic circular corners and connecting straight
segments use the connected bezierpath backend, with exactly pinned joins.

Creation, path motion, rotation/scaling, primitive morphing, copying and Restore
therefore share existing behavior. Tests cover corner correspondence, concavity,
clamping, collapsed dimensions, transformed queries, validation, primitive
alignment and gallery restoration. General polygon rounding, native point-array
editing and rectangle grids remain open.

Local Pyodide playback verified a closed twelve-segment rounded outline at two
seconds, alternating concave/convex corners at eight seconds, and the restored
blue outline without the follower at eleven seconds. Graphviz rendered after
switching examples.


## Disconnected contours and alignment

VMobject supports start_new_path, has_new_path_started, close_path and get_subpaths
using the [official path construction and per-contour alignment model](https://docs.manim.community/en/stable/_modules/manim/mobject/types/vectorized_mobject.html).
An unfinished anchor is retained separately until the next straight/cubic append;
starting another contour completes the previous unfinished anchor as a null curve.
Queries return transformed, independent lists of anchors/handles; pending anchors
are excluded from subpaths. Reverse completes any pending anchor then reverses
curve order and direction. Existing replacement, copying and checkpoints apply.

Flat cubic snapshots group connected anchor pairs into separate contours. SVG
emits a new M at each boundary and Z only for that contour's matching start/end,
so holes and open segments have no artificial connector. Path motion sums actual
curve lengths and jumps across gaps. Aligned snapshots carry integer contour
lengths so collapsed/coincident paths keep their boundaries.

Transform aligns ordered contour pairs independently through exact subdivision.
Missing contours become null curves at the other path's final endpoint, matching
the native strategy. Annulus converts into outer and reversed inner circles.
Matching annuli retain analytical radius interpolation. All native target/checkpoint
representations return at completion. This supports nested family morphs through
the existing transform plan; automatic contour correspondence, boolean geometry,
general point-array semantics remain open.

Tests cover pending anchors, atomic validation, independent queries, closure,
reversal/copy/checkpoints, gap-free length sampling, equal-total/different-contour
counts, null-contour alignment, ring morph restoration, integer boundary metadata,
SVG moves/closure/tracing and gallery restoration.

Local Pyodide playback verified two closed square contours at two seconds,
two closed morph contours with sixteen cubics at seven seconds, a shrinking
hole with twenty cubics at nine seconds, and restoration of both blue square
contours at thirteen seconds. No radial connector was drawn. Graphviz rendered
after switching examples.

## Raw cubic point arrays

Supported outlines expose get_points/get_num_points/has_points. Point queries
return independent world-space coordinate lists: four anchors/handles per cubic,
plus an optional unfinished anchor. Primitive queries use existing cubic outline
conversion. Geometry without a supported outline returns an empty list.

VMobject implements set_points, append_points, clear_points, add_subpath and
append_vectorized_mobject, following the [official raw-point operations](https://docs.manim.community/en/stable/_modules/manim/mobject/types/vectorized_mobject.html).
Arrays validate finite XY points and lengths of 4n or 4n+1 before mutation;
add_subpath requires 4n. Replacements use world coordinates. Append bakes old
transforms and preserves earlier points; start_new_path now does the same to
avoid changing the rotation pivot when an unfinished anchor expands the bounds.
Neutral transforms avoid unnecessary floating-point subtraction/readdition.
Copied vector outlines are independent, retain receiver styles and drop the
receiver's unfinished anchor as native append_vectorized_mobject does.

Styles/callbacks/checkpoints survive editing. Animate accepts the raw methods,
start_new_path and close_path; existing morph alignment samples intermediate
geometry and restoration. Empty endpoint queries report a clear error. Tests
cover transformed round trips, alias isolation, pending completion, invalid
input atomicity, clearing/restoration, copied outline appends and gallery output.
General NumPy semantics, direct mutable points attributes and glyph point access
remain open.

Local Pyodide playback verified raw pending-anchor completion, animated handle
edits and appended ring geometry. At four seconds the preview contained three
separate contours and seventeen cubics; at eight seconds Restore returned the
original single curve. Graphviz rendered after switching examples.

## Exact partial curves

Supported outlines implement get_subcurve and pointwise_become_partial using
the [official cubic-index selection and wrap behavior](https://docs.manim.community/en/stable/_modules/manim/mobject/types/vectorized_mobject.html).
Finite fractions clamp to [0,1]; source curve count determines the lower/upper
indices and local residues. Exact De Casteljau splits trim only boundary cubics;
interior curves remain unchanged. An exact boundary may include the next curve
as a null segment, matching native selection. Zero-length intervals collapse to
one point. Full-range copying includes a pending anchor; a partial request with
no completed source curves leaves the receiver unchanged.

Pointwise replacement keeps receiver styles, callbacks and checkpoint. Queries
return independent copies, and get_subcurve wraps reversed intervals on outlines
whose first/last anchors coincide (is_closed); direct reversed partial replacement
raises an error before mutation. Geometry is baked to world coordinates, preserving
transformed source shape. Integer contour lengths retain disconnected boundaries.
get_num_curves counts completed cubics. Animate accepts partial replacement, and
native target/checkpoint representations use the existing transform pipeline.

Tests cover exact cubic parameter correspondence after transforms, source/copy
independence, receiver styles, unequal straight segment lengths, boundary null
curves, disconnected/self partial replacement, ring endpoints, closure/wrapping,
clamping/invalid/empty inputs and gallery cleanup. This supplies partial geometry;
broader partial-creation animations and glyph outlines
remain implementation work.

Local Pyodide playback verified the yellow exact cubic portion and a blue
four-cubic circular highlight wrapped across the positive-X endpoint at four
seconds. Animated replacement selected the curve's final portion; at eight
seconds both highlights were removed and the original gray curve and circle
remained. Graphviz rendered after switching examples.

## Traveling outline highlights

ShowPassingFlash implements the moving window described in the official
[Manim indication source](https://docs.manim.community/en/stable/_modules/manim/animation/indication.html):
upper = (1 + time_width) * alpha, lower = upper - time_width, clipped to [0,1].
Fractions allocate by cubic index, rather than physical distance. Default width
is .1; zero and widths greater than one are accepted. Widths must be finite,
nonnegative real values. Existing animation easing and run_time apply.

The animation introduces its object, samples exact partial geometry from an
independent start copy and removes it at completion. Live geometry, styles,
callbacks and checkpoints remain available for subsequent animations. Use a
styled copy to retain the visible original. Each supported group child uses the
same window; group transform pivots remain fixed while clipped child bounds
change. Validation rejects unsupported glyphs/arrows before adding the object.
Per-child lag, general glyph geometry and broader passing-flash variants remain
open; this does not change Create's existing SVG stroke reveal.

Python checks cover exact transformed clipping, width endpoints/validation,
fixed nested-group pivots, empty objects, removal, checkpoint restoration and
reuse in Succession. The gallery renders nine seconds with simultaneous curve
and group highlights, followed by two sequential flashes on the same object.
Local Pyodide playback verified yellow/blue sections aligned with gray original
outlines at two seconds and their removal at nine seconds. Switching to the DOT
example rendered Editor → Render → Preview successfully.

## Linear numeric coordinates

NumberLine supplies the linear coordinate foundation for graphing, following the
[official NumberLine API](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.number_line.NumberLine.html).
The renderer sees an existing VGroup containing a tagged shaft, optional tip,
ticks and numeric labels. Child roles are strings rather than object references,
so snapshots remain JSON-safe and copy/restoration do not leave stale aliases.
The complete group participates in creation, transformation and animation.
General geometry-bearing family/path semantics remain open.

Numeric conversion interpolates the current world shaft endpoints and allows
extrapolation. Inverse conversion projects onto the shaft direction, including
points away from it, and rejects a collapsed shaft. Queries compose the shaft
transform with the NumberLine parent transform. During animation, dependent
updaters read the temporarily exposed sampled family and parent pivot; they do
not use the held terminal geometry early. Lists/tuples of scalar numbers are
accepted by n2p; NumPy arrays and batch inverse conversion remain open.

Ticks crossing zero use multiples of the configured step; wholly positive or
negative ranges begin at their minimum. Tip endpoints exclude the final tick.
Numeric labels use DecimalNumber's existing SVG text and decimal formatting;
font metrics, TeX label factories and logarithmic scaling remain open. Tick and
label additions are limited to 1000 each. Decoration construction validates
before insertion. On a transformed NumberLine, new world geometry is mapped
into parent coordinates and its changed bounding-box pivot is compensated,
keeping existing world endpoints and decoration positions fixed.

Python checks cover range/length/format validation, bounded additions, zero
anchoring, tips and elongated ticks, scalar/batch conversion, projection and
extrapolation, rotation/scaling, transformed decoration insertion, copies,
restoration, animated resizing and dependent marker sampling. Local Pyodide
playback verified the marker at the tracked numeric position while the shaft
rotated/shrank/moved. At eleven seconds, restoration returned a horizontal line
and the marker/readout to zero. Switching to DOT rendered the editor flow graph.
Broader graphing APIs remain implementation work.

## Cartesian axes

Axes builds two NumberLines using the
[official coordinate-system API](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.coordinate_systems.Axes.html).
Shared configuration applies before per-axis overrides; numeric-format dictionaries
merge. Defaults include tips, omit zero labels/ticks and place y labels to the
left. The coordinate rectangle is centered, including positive-only or
negative-only ranges. Child roles identify the actual x/y NumberLines without
putting Mobject references into JSON or retaining stale aliases after copies.

c2p composes child coordinate queries with the Axes parent transform. p2c solves
the current XY basis, rejecting collapsed or nearly parallel axes. World unit
sizes and the numeric origin use the same nested transforms. Lists/tuples support
single coordinates, row batches, paired coordinate lists and scalar broadcasting;
inverse conversion accepts points or point rows. Batches are limited to 1000.
Nonzero z coordinates, NumPy arrays and nonlinear coordinate scales remain open.
Child axis getters retain the existing group's local-coordinate semantics.

Coordinate labels are prepared on copies of both axes before mutating either
live axis. After insertion, parent pivot compensation preserves world geometry
when the bounds change. Axis labels use supplied Mobjects or existing MathTex
strings. Independent child animation, generalized family geometry, glyph bounds,
Broader graphing APIs remain implementation work.

Python checks cover all-sign ranges, rectangular centering, nested transforms,
extrapolation, inversion of unequal/skewed bases, scalar/batch conversions,
configuration isolation/merging, role identity, labels, atomic invalid additions,
transformed insertion, copies and invalid/collapsed/parallel cases. The gallery
explicitly samples a polyline and uses updaters to follow the current coordinate
frame; it does not imply an Axes.plot implementation. Local Pyodide playback
verified the marker and blue curve on rotated/scaled axes at seven seconds.
At eleven seconds, restoration returned the frame and marker to (0,-1) in axis
coordinates. Switching to DOT rendered the editor flow graph.

## Function plotting and smooth paths

ParametricFunction samples finite XY scene points, FunctionGraph wraps scalar y
functions, and Axes.plot/plot_parametric_curve map functions through the current
Cartesian frame. This follows the
[official function API](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.functions.ParametricFunction.html)
and [Axes plotting](https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html).
Two-item parametric ranges default to .01; Axes uses ten samples per tick unless
an explicit step or num_sampled_graph_points_per_tick changes the density.
Exact final parameters are included. Sampling is bounded to 10001 points before
callbacks run; invalid output never partially replaces existing geometry.
Providers remain runtime-only and are excluded from frame JSON.

Default smooth interpolation uses C2 cubic splines, with natural open endpoints
and a periodic closed system. The pure-Python tridiagonal solver avoids a new
NumPy/SciPy runtime dependency. The closed solve uses a rank-one correction;
rounding-close endpoints share a seam anchor so SVG closes the contour. See the
[official spline equations](https://docs.manim.community/en/stable/_modules/manim/utils/bezier.html).
VMobject smooth/jagged conversion operates contour by contour, retains pending
anchors and compensates changed handle bounds while preserving its transform.
Thus interpolating handles during animated smoothing keeps world anchors fixed.

Declared discontinuities exclude buffered intervals; overlapping gaps merge.
Each remaining interval samples independently with no connecting segment.
Nonfinite samples and non-XY geometry fail explicitly. Scalar graph input
queries evaluate the original function in the current axes, rather than moving
with independent graph transforms. Fresh plots are independent geometry;
always_redraw regenerates them when their parameters or frame change.
Vectorized callbacks, adaptive sampling, nonlinear/color scales, implicit plots,
Broader graph analysis remains open.

Tests cover exact open handles, periodic first/second derivative continuity,
degenerate loops, contour/style/checkpoint preservation, animated transformed
anchors, endpoint sampling, discontinuity exclusion/merging, bounded validation,
atomic regeneration, standalone graphs, axis mapping/density and runtime-only
callbacks. Local Pyodide rendered the changing parabola, tracked marker, yellow
passing highlight and a closed 32-cubic red loop. At eleven seconds only the
axes and final blue 40-cubic plot remained. Switching to DOT rendered the editor
flow graph.


## Cartesian grids

NumberPlane adds major and faded Cartesian lines using the
[official grid conventions](https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html).
Ranges default to the configured frame and lengths to the numeric spans, giving
unit scale. Axes omit ticks/tips and use 24-point labels. Default major strokes
use BLUE_D; faded strokes halve numerical style values unless explicitly supplied.
A nonnegative integer faded_line_ratio controls subdivisions; zero means no
faded lines. Grid offsets follow the native origin-relative sequences, excluding
outer boundaries; zero-offset lines follow the native major/faded classification.
Preflight counts reject grids exceeding 1000 lines before allocation.

Tagged background/faded groups precede the axes. Their lines use Axes-local
coordinates, so inherited conversion, label pivot compensation and sampled
transforms remain consistent. Major horizontal/vertical getters build local
views of the actual children, preserving copy/restore identities without putting
Mobject aliases in frame JSON. get_vector creates a world-space Arrow whose
endpoints touch the numeric origin and requested coordinate; always_redraw keeps
it synchronized with changing axes. The smoothing flag is metadata only;
nonlinear transform preparation and application remain implementation work.

Tests cover subdivisions, styles, nonzero ranges, default lengths, local roles,
transformed labels/vectors, copies, restoration, invalid inputs, allocation limits
and sampled marker alignment. The gallery combines a dynamic vector with a red
function plot on a rotating/scaling plane, then restores the plane and removes
the marker/vector.

Local Pyodide playback verified 18 styled grid lines, the red curve and a yellow
vector touching its marker on the rotated/scaled plane at seven seconds. The
final eleven-second frame restored the grid and removed the marker/vector.
Switching to DOT rendered the editor flow graph. All 242 Python and 72 Node
tests passed for this update.


## Complex coordinates

ComplexPlane uses NumberPlane's grid and transform-aware basis. Its scalar n2p
and p2n methods follow the
[official complex-plane API](https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html).
Finite complex-compatible input maps real and imaginary components to c2p;
p2n inverts the current XY basis. get_coordinate_labels creates independent
world-positioned numeric labels. Defaults use the x/y tick ranges; explicit
values choose the larger-magnitude component, with ties selecting real. Imaginary
labels append i. Formatting dictionaries stay independent between labels.

add_coordinates maps those labels into parent-local geometry, counteracting its
rotation/scale, then compensates the changed bounding-box pivot. Existing world
coordinates remain fixed. Attached getters find tagged children; runtime-only
unattached aliases are excluded from JSON. Invalid values/options and oversized
label sets fail before mutation. Numeric glyph bounds still use the existing Text
approximation, and complex warping/nonlinear transforms remain open.

Python tests cover round trips, nonzero ranges, transformed labels, formatting,
option isolation, copies, become/restore, atomic validation and conjugate marker
sampling. The gallery tracks a rotating complex value and its conjugate, rotates
and restores the plane, then removes the vector while retaining the two points.

Local Pyodide playback verified the conjugate markers and vector on the rotated
plane at seven seconds, then restored the yellow point to 2i and green point to
-2i at eleven seconds. Imaginary axis labels rendered as numeric SVG text and
switching to DOT rendered the editor flow graph. All 247 Python and 72 Node
tests passed for this update.


## Numerical graph calculus

The scalar graph-query foundation now includes input_to_graph_coords/i2gc,
angle_of_tangent, slope_of_tangent, plot_derivative_graph and
plot_antiderivative_graph, following the
[official coordinate-system calculus API](https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html).
Queries validate finite real input/output. Forward differences use the actual
representable input increment (default requested dx=1e-8), reject zero or
unrepresentable increments, and return numeric-coordinate slope/angle. They do
not change with world rotation or unequal axis scale.

Derivative plots sample those slopes. Antiderivative plots evaluate the original
scalar provider on evenly spaced signed intervals from zero, then sum trapezoid
areas and add y_intercept. Sample count is bounded to 2–10000; all intermediate
values and results must remain finite. Ordinary plot preflight still bounds
geometry counts before invoking callbacks. No graph/source mutation occurs;
provider closures stay out of frame JSON and retain normal copy behavior.

Both plotting helpers default to the axes' range. Declared plot discontinuities
split result contours but do not skip singularities inside an integration
interval. Vectorized functions and symbolic/adaptive calculus remain open. Python tests cover numeric coordinates,
signed dx, transformed/scaled frames, derivative samples, signed integrals,
intercepts, convergence, provider isolation and invalid inputs. The gallery
combines sine, its derivative, recovered sine, a moving tangent and numeric slope.

Local Pyodide playback verified three 40-cubic plotted curves, a tangent touching
the origin at five seconds and a 1.00 slope readout. The final nine-second frame
retained the curves and removed the tangent/marker/readout. Switching to DOT
rendered the editor flow graph. All 252 Python and 72 Node tests passed.


## Riemann area estimates

get_riemann_rectangles follows the sampling, default range, signed coloring and
bounding-baseline behavior of the
[official Riemann API](https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html).
Partitions exclude the upper starting input, but the final rectangle may extend
past the requested end. dx overrides a third range item. Sampling is left/right/
center; a bounding provider uses the left input for the baseline, otherwise zero
is clamped into the y range. Default bounds come from the graph or the intersection
of two graphs. Invalid ranges/counts/styles fail before invoking callbacks.

Rectangle instances retain their class identity and serialize four polygon
corners, so cells follow the current XY basis rather than a world-aligned bounding
box. This intentionally preserves coordinate geometry on transformed axes.
Positive width scale includes the chosen sample, with default slight overlap.
Hex gradients use up to 64 stops; signed negative heights invert RGB channels.
Fill opacity, border width/color and blended borders are supported. Groups cap at
1000 cells. Cells are independent snapshots; changing axes/functions requires
regeneration. Plot discontinuities do not suppress sampling. General color
objects remain open; continuous polygons are described below.

Tests cover sampling choices, signed/unsigned colors, gradients, blended strokes,
Rectangle identity, open last intervals, bounded/default ranges, clamped origins,
transformed corners, source isolation, copies/restoration, validation and gallery
refinement/cleanup. The gallery refines eight signed cells to 32, transforms them
into 16 cells between two functions, then removes the cells and bounding curve.

Local Pyodide playback verified 32 refined cells before four seconds and 16
signed cells between the parabola and line at six seconds. The final eight-second
frame removed the cells and bounding curve. Switching to DOT rendered the editor
flow graph. All 258 Python and 72 Node tests passed.


## Labeled secant groups

Axes.get_secant_slope_group follows the [Community secant API](https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html):
world-horizontal dx, world-vertical df, default interval one tenth of the x range,
and an optional fixed-length secant centered between the graph points. Negative
intervals reverse label sides. Strings and finite numbers become MathTex;
Mobject label templates are copied. Independent style colors are supported.
Role-tagged direct children expose components without serializing Mobject aliases,
so copies, become, restore and dynamic redraw keep getters consistent.

Label shrink/spacing uses font-size and character-count estimates because glyph
metrics are browser-owned. Complex TeX can exceed those estimates; measured font
layout remains open. Geometry labels use existing conservative bounds. Both
changes constrain label sizes; flat or vertically collapsed spans collapse labels.
Input validation rejects nonfinite values, invalid labels, unrepresentable dx and
collapsed extended lines without modifying the graph or axes. Tests cover signed
intervals, transformed axes, styles, copied templates, role lifecycle, validation,
and gallery frame redraw and cleanup.


Local Pyodide playback verified both formula labels and the three colored lines
at two seconds, interval refinement at five seconds, input motion at seven seconds,
and removal at nine seconds. Switching to DOT rendered the editor flow graph.
All 263 Python and 72 Node tests passed.


## Continuous graph regions

Axes.get_area follows the [Community area construction](https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html):
endpoint provider evaluations enclose existing plotted points inside the selected
numeric interval. These include cubic control points and become Polygon vertices,
rather than a resampled smooth boundary. The unbounded baseline is numeric zero,
including when zero lies outside the displayed y range. A bounding graph contributes
its reversed boundary and clips the selected interval to its parameter range;
nonoverlapping ranges fail. Explicit primary ranges may extrapolate endpoint
providers beyond the plot range, as in Community. Degenerate intervals are finite
but have zero filled area. Plot gaps are bridged by polygon edges.

Styles and ranges validate before endpoint calls, without source mutation. A hex
color or 1–64 hex stops gives solid paint or a left-to-right SVG bounding-box
gradient. This is an SVG approximation of Community shading. Separate fill/stroke
paint servers have unique IDs across frames/shapes, are wrapped with their geometry
under the same transform, and remain inline for export. Opacity controls both
channels; geometry bounds, copies, restoration, ordinary morphing and redraw use
the existing pipeline. Broader color objects and disconnected/singular regions
remain open.

Tests cover exact endpoints/interior points, defaults, bounded intersection and
reversal, zero and negative areas, transformed axes, styles, source isolation,
validation before callbacks, dynamic bounds, gradient morphing and removal. SVG
tests verify multiple stops, independent borders, unique IDs, transforms and
invalid-color rejection. Local Pyodide playback verified the expanded blue/green
region at 4.9 seconds and red/yellow region between curves at seven seconds.
The nine-second frame removes all gradients and the bounding curve. The SVG
export contains inline gradients and local paint references; PNG export reported
success. Switching to DOT rendered the editor flow graph. All 268 Python and 74
Node tests passed.


## Dashed lines and coordinate projections

DashedLine follows the [Community straight-dash convention](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/line.html):
count is max(2, ceil(length / dash_length * dashed_ratio)), with occupied fraction
ratio/count per dash and equal gaps between them. Dash length must be positive
and finite; ratio is finite in [0,1], with a preflight cap of 1000 dashes. The
class inherits Line and VGroup behavior, serializes a vgroup with actual Line
children, and has no own path points. Start/end and first/last handles query the
children through the parent transform. Styles propagate normally. Endpoint
changes map the existing child endpoints by a uniform rotate/scale/shift, retaining
individual geometry/color edits and fixed count. Collapsed lines recover from
stored dash intervals. Curved DashedVMobject construction is described below.

Line and NumberLine projection uses the infinite world-space shaft; collapsed
shafts return the start. Axes [coordinate guides](https://docs.manim.community/en/stable/_modules/manim/mobject/graphing/coordinate_systems.html)
project onto fully transformed axis endpoints. Vertical means from the x-axis;
horizontal means from the y-axis, including when axes are rotated or skewed.
get_lines_to_point returns horizontal then vertical. DashedLine is the default;
Line or another Line-returning callable can be supplied. Configuration dictionaries
are copied, with helper color/default white and stroke-width/default 2 overrides.
World-space guide snapshots need regeneration when the axes or point changes.

Python tests cover dash counts/occupied ratios, end handles/styles, zero spans,
transforms, fixed-count endpoint animation, edited segments, zero-scale recovery,
copy/restore, finite validation, caps, projection/extrapolation/collapse, skewed
axis geometry, config isolation and gallery redraw/cleanup. Local Pyodide playback
showed 21 dash segments and both guide endpoints meeting the marker after the
30-degree rotation at seven seconds. The nine-second frame removed the dashes and
marker. Switching to DOT rendered the editor flow graph. All 275 Python and 74
Node tests passed.


## Curved dashed geometry

DashedVMobject follows the [Community spacing/phase API](https://docs.manim.community/en/stable/_modules/manim/mobject/types/vectorized_mobject.html)
for supported XY outlines. It creates actual copied subcurve children, preserving
source styles without mutation. Requested counts are integers from 0 to 1000;
ratios are finite in [0,1], offset is finite, and spacing flags are boolean.
Zero count returns an empty group. Closed curves have equal numbers of dashes and
gaps; open curves end with a dash at zero phase. Offset wraps modulo one period,
with open end clipping or a new beginning piece when the pattern overflows.
Closed seam cuts use the existing exact wrapped get_subcurve implementation.
One-dash full coverage remains a full closed path at arbitrary phase, handling
the otherwise ambiguous equal start/end parameters explicitly.

Equal-length spacing samples 20 pieces per cubic and inverts cumulative distance
with a binary lookup, then uses exact parameter subdivision. Legacy parameter
spacing skips that inversion. Curve-length lookup resets at each cubic, so contour
gaps do not add phantom distance. The resulting parts retain separate contours.
Lookup work caps at 200000 segments. get_arc_length uses the same finite sampling
helper with a configurable 2–1000 points per curve, default 10. Constant curves
measure exactly zero. Arc length is approximate, not analytic or adaptive.

The container has VMobject and VGroup behavior but no own points; it stores no
source aliases or lookup arrays. Copies, checkpoints, family styles, redraw,
creation, group morphing and removal use the existing pipeline. Source Line copies
converted to cubic paths now read actual path endpoints. Source callback copying
uses existing subcurve semantics. Arrow tips, glyphs and general geometry-bearing
source families are unsupported and remain completion gates.

Tests cover native open spacing, source styles/isolation, both spacing modes on
unequal straight segments and curved cubics, circle measurement, closed phase
wrap/full coverage, signed offsets, open clipping/reappearance, zero ratios/counts,
collapsed outlines, disconnected contours, transforms/copies/restoration, limits
and gallery phase/refinement/cleanup. Local Pyodide playback verified twelve ring
dashes and eight equal-length dashes at two seconds, changed phase before five
seconds, and sixteen refined red dashes at seven seconds. The final nine-second
frame retained only reference geometry and labels. Switching to DOT rendered the
editor flow graph. All 282 Python and 74 Node tests passed.


## Path tangents and line controls

TangentLine implements the [Community path-tangent construction](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/line.html):
sample around a path proportion, clip to [0,1], and extend the sample chord to a
requested length around its midpoint. It uses existing world-space outline
queries, including transformed circles/ellipses and cubic paths. Styles come from
Line kwargs; no source alias is serialized. Positive finite sample distance,
finite proportions in [0,1] and nonnegative finite lengths validate before sampling.
Coincident samples or a distance that cannot change the proportion fail. A full
closed-path chord is rejected explicitly because tiny closure rounding residuals
do not define a direction. Resolved tiny spans normalize component by component.
Zero requested length produces a finite collapsed line. Corners/disconnected
contours can yield a chord through a nonsmooth point; no analytic tangent is
claimed. Ordinary path sampling approximations still apply.

Line.get_slope returns tan of the current angle. set_angle defaults to rotating
around the current start, accepts an explicit pivot and is whitelisted for animate;
NumberLine aliases this behavior. Line.set_length scales about its current center
and accepts zero, while collapsed/nonfinite spans cannot be resized. DashedLine
inherits these transforms over its actual child family without recomputing count.
NumberLine retains its previous positive resize contract. Checkpoints and endpoint
replacement provide the existing zero-scale recovery paths.

Tests cover circular directions, midpoint/endpoint clipping, style/source
isolation, transformed ellipses, cubic chord sampling, corners, tiny resolved
spans, nonrepresentable sampling, closed/degenerate paths, input/style validation,
angle anchors, lengths/centers, dashed count preservation, numeric-axis angles,
animate and gallery redraw/removal. Local Pyodide playback verified tangents
moving from 1.8-unit lengths at two seconds to 3-unit lengths at seven seconds,
with their chord midpoints matching the markers within floating-point precision.
The nine-second frame removed tangent lines and markers while retaining source
curves and labels. Switching to DOT rendered the editor flow graph. All 287 Python
and 74 Node tests passed.


## Angle and corner marks

`Angle`, `RightAngle` and `Elbow` now support static and redrawn XY angle marks.
Two finite Line shafts define their infinite-line intersection. Quadrant signs
select the positive/negative shaft rays. Circular sweeps are counterclockwise by
default and clockwise with `other_angle=True`. Automatic radius follows the
selected endpoint distances (two-thirds of the shorter distance below .6,
otherwise .4). Parallel/zero-length shafts produce empty geometry. Explicit
radii and dot distances must be finite and nonnegative. RightAngle makes an
elbow between the selected rays, including nonperpendicular inputs; it does not
assert perpendicularity. Standalone Elbow rotates about the origin.

Angle now stores its own cubic arc/corner outline, with the optional dot as a
child, matching native own-path/dot structure. Creation, opacity, transforms,
copy, redraw and removal use geometry-bearing family support. Native mutable
NumPy points and glyph-level family semantics remain open. `get_lines` preserves the
source references; they are omitted from frame JSON. `get_value` returns the
construction-time signed sweep in radians or degrees (including elbow marks).
The mark is a snapshot: use `always_redraw` for line motion. Dot placement follows
the arc bounding-center direction, with a stable intersection fallback at zero
radius. The gallery combines a changing angle/degree label, right corner and
clockwise three-quarter arc, then removes all marks.

Python checks cover quadrants, direction, automatic radii, defining references,
dot positions, source isolation, elbow endpoints/rotation, empty cases,
validation, JSON isolation and gallery redraw/removal.

Reference: [official Manim geometry implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/line.html).

Local Pyodide playback verified a yellow quarter-circle at seven seconds, a
green independently colored dot, a green two-segment elbow, a red clockwise
three-quarter arc and the changing label ending at 90 degrees. At nine seconds
all mark paths and dots were removed. Switching to the DOT gallery rendered
the Editor → Render → Preview graph successfully.


## Endpoint-defined arcs

ArcBetweenPoints now constructs circular paths between finite XY endpoints using
signed sweeps shorter than one turn. Its center is the chord midpoint plus the
left normal times half the chord length divided by tan(angle/2). Its radius is
half the chord length divided by abs(sin(angle/2)). Positive sweeps are
counterclockwise; negative sweeps clockwise, with major arcs supported.
An explicit signed radius overrides the angle using twice the signed arcsine
of half-chord/radius, selecting a minor arc. Too-small, zero or nonfinite radii
are rejected. Zero angle creates a straight polyline, and coincident endpoints
collapse to a point. These cases serialize finite values rather than native
straight-arc infinite-radius metadata. Full turns and endpoints that cannot be
resolved at floating-point precision are rejected. The existing Arc query,
partial-curve, transform, restore and morph pipeline supplies playback geometry.

The gallery redraws positive-angle and negative-radius arcs as one endpoint
moves, then reduces the positive bend to zero and removes both paths. Python
checks cover positive/negative minor and major sweeps, center/radius calculation,
endpoint alignment, radius precedence, zero/coincident cases, world transforms,
partial extraction, restoration, validation, precision and gallery cleanup.
General 3D arcs, mutable native points and general Arc/Circle tip attachment remain open.

Reference: [official Manim arc implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html).

Local Pyodide playback verified both oppositely directed arcs at five seconds,
the yellow straight chord at seven seconds and removal of both paths at nine
seconds. The DOT gallery still rendered the editor flow graph. All 295 Python
and 74 Node tests passed for this change.


## Arc polygons and geometry-bearing families

ArcPolygon now builds a closed cubic outline from two to 256 finite XY vertices,
with shared angle/radius defaults or a shared/per-edge configuration dictionary.
ArcPolygonFromArcs accepts up to 256 Arc-family objects, preserving references to
them as children while copying their world-space curves into its own outline.
Inter-arc gaps and closure receive straight cubic segments. Joins within 1e-9
world units are snapped to avoid accidental separate contours caused by circular
endpoint roundoff. Empty input to ArcPolygonFromArcs produces an empty path.
`.arcs` reflects current children, so copying, become and restoration avoid stale
aliases. Existing child edits do not regenerate the copied outline, matching its
construction-time nature; use redraw to regenerate it. Parent styling applies
to the polygon; edge config or existing arcs preserve independent edge styling.

The SVG layer collector now paints non-group objects' own geometry and their
children. Child branches inherit the ancestor's transform and opacity without
repainting its path or overriding child styles. Both own geometry and descendants
participate in global numeric depth sorting. Create now reveals own geometry and
children together. Transform plans align the own path and child family separately,
allowing filled curved polygons to morph with visible colored edges. Arc polygon
children are converted to parent-local cubic snapshots before alignment so their
interpolation follows the copied outline rather than separate analytical circle
parameters. Their
independent curve subdivision can differ for unrelated shapes; automatic edge
correspondence, arbitrary scene restructuring
remain open. Child queries retain the runtime's local-to-parent convention.

Python checks cover closure, straight gap bridges, transformed input snapshots,
config/source isolation, copied child aliases, restoration, creation, morphs,
input validation and gallery cleanup. Renderer checks cover all paths, independent
styles, ancestor transforms/opacity and depth ordering across an outside shape.

Reference: [official Manim arc polygon implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html).

Local Pyodide playback verified the blue closed fill and three colored arcs at
two seconds. At six seconds the fill remained closed and each edge used two
cubic segments aligned with the six-segment outline. All paths disappeared at
nine seconds, and switching to DOT rendered the editor flow graph. All 299
Python and 75 Node tests passed.


## Editable angle paths

Angle is now a VMobject with its own cubic arc/corner path, rather than a VGroup
with a separate geometry child. `get_points`, endpoint/proportion queries,
reversal, partial extraction and point replacement operate on that own path.
Only the independently colored dot is a child. `.lines` exposes the defining
line references, also returned by `get_lines`; those references stay out of
frame JSON. Parallel/zero-span angles remain empty paths. Dot geometry is not
included in own point arrays. Existing `get_subcurve` copies may retain the dot
child; use the extracted points in a fresh VMobject for an outline-only highlight.

The new gallery moves a marker along the dotted angle, morphs the angle into a
right corner (removing its dot), restores the checkpoint including its dot, and
removes the marks. Python checks cover the own-path/family structure, construction
queries, transformed endpoints, reversal, restored geometry, copied point edits,
partial length, JSON isolation and gallery restoration/cleanup.

Local Pyodide playback verified a red two-segment corner at seven seconds and
the restored yellow arc/green dot at eight seconds. Both angle and moving marker
were absent at ten seconds. Switching to DOT rendered the editor flow graph.
All 301 Python and 75 Node tests passed.


## Common Mobject family API

Child validation, add/add_to_back/remove and submobjects replacement now belong
to Mobject, so ordinary shapes and paths can retain child geometry without a
special group wrapper. Mutation preserves identity, removes duplicate references,
checks full descendant cycles and excludes camera frames from display families.
Invalid batches do not partially change children. Angle and arc polygons inherit
the common API rather than borrowing Group's methods.

For non-group objects with extractable points, split/iteration/indexing include
self first and then direct children. Slices share those references in a fresh
neutral Group/VGroup. Empty paths and base Mobject containers index children only;
Group/VGroup retain their existing child-only behavior. `family_members_with_points`
filters the deduplicated recursive family by supported own-path geometry. Text,
MathTex point extraction is still incomplete, so these queries do not claim
native glyph families. Arrow own points now expose its shaft and tips are children. Empty base Mobject containers have no SVG shape
but their descendants inherit their pose and opacity.

The gallery creates a rectangle and attached dots, rotates/translates it, adds a
nested circle/dot, removes one dot, restores the checkpoint and removes the
family. Python checks cover mutation ordering, duplicates, atomic rejection,
cycle/camera exclusion, self inclusion, reverse slices, identity sharing, family
filters, copy/restore, callbacks, serialization and gallery timing. Renderer
checks cover point-free containers and inherited translation. Own-plus-child union bounds now support layout/framing; general scene
restructuring remains open.

Reference: [official Manim Mobject implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).

Transform completion now delegates to identity-preserving become, retaining
ordered live child references, child callbacks and checkpoints. Previously the
terminal replacement silently copied children, breaking later removal through
a saved child reference. Tests explicitly cover that reference/removal behavior
and replacement with a differently shaped family.

Local Pyodide playback verified the rectangle with a nested red circle/white dot
and two colored child dots at four seconds. Removal through the original yellow
dot reference left three circles at five seconds; restoration returned exactly
the original yellow/green dots at eight seconds. No child circles remained at
ten seconds. Switching to DOT rendered the editor flow graph. All 306 Python
and 76 Node tests passed.


## Own-plus-child bounds and stable attachment

Family local bounds now union the parent's supported own geometry with nested
child bounds. Empty path/container parents do not add an origin box. Circle and
ellipse analytical shortcuts apply only without children; families use a
conservative enclosing box so distant children are included. Public width/height,
left/right/top/bottom, critical-point, edge-center and corner queries now expose
the XY bounds. next_to and camera.auto_zoom use those same bounds.

On ordinary geometry-bearing objects, add/add_to_back/remove/submobjects
replacement preserve the existing affine mapping when child insertion changes
the bounding-center pivot: position shifts by A(delta)-delta. This covers rotation,
uniform scaling and collapsed parents. Group mutations now share this behavior, as described in the nested-group
section below. Coordinate helpers use the common compensation.
Native world-space child mutation semantics remain incomplete. Direct child
motion now preserves ordinary shape and Group/VGroup parents, as described below.
Bounds also remain conservative for rotated composite boxes/cubic handles, and
text/glyph metrics remain incomplete.

The gallery keeps a red reference on a rotated rectangle corner, adds distant
children, displays the enclosing boundary, fits the camera twice and removes the
family. Python checks cover nested union, public queries, finite XY validation,
attachment/reordering/removal/replacement pose preservation, next_to, camera
containment, collapsed geometry, reference-anchor invariance and gallery cleanup.

Reference: [official Manim boundary queries](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).

Local Pyodide playback verified green/purple distant children and a red corner
reference, with camera scale changing from about 2.43 to 1.83 as the fitted
selection expanded. All family circles disappeared at ten seconds. Switching to
DOT rendered the editor flow graph. All 310 Python and 76 Node tests passed.


## Moving children inside transformed ordinary shapes

Ordinary geometry-bearing parents now keep their affine mapping when moving or
resizing a child changes the family bounding-center pivot. A private cache tracks
own bounds, child bounds and the last local pivot. When child bounds change and
own geometry stays fixed, position shifts by A(delta)-delta. Nested parents
synchronize through bounds queries; pose changes and serialization synchronize
before consuming position. Explicit child replacement resets the cache before
its existing compensation, and sampled frames keep their pinned geometry center.
The cache uses bounds rather than identities, survives copying/checkpoints, and
is excluded from frame JSON.

The gallery moves a tracked yellow dot inside a rotated/scaled rectangle while
a green sibling and red corner reference remain fixed. Tests cover negative/zero
scales, nested motion, child resizing, copy/restore isolation, serialization and
final cleanup. This retains browser local-to-parent coordinates; native recursive
world-point mutation semantics remain unfinished. Group/VGroup use the same
compensation, as described below.

Reference: [official Manim Mobject implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).

Local Pyodide playback verified unchanged parent/sibling world transforms at two
and seven seconds while the yellow dot moved, and no circles remained at nine
seconds. Switching to DOT rendered the editor flow graph. All 314 Python and
76 Node tests passed.


## Stable nested Group and VGroup children

The shared family-pivot cache and explicit child replacement compensation now
also apply to Group, VGroup, NumberLine, Axes and plane families. Moving or
resizing a child, attaching/reordering/removing children and replacing the child
list preserve stationary siblings through nested rotated/scaled ancestors.
Empty-to-populated transitions preserve the same affine mapping. Coordinate
helpers no longer add separate manual shifts after shared compensation, avoiding
double adjustment when labels or ticks change family bounds.

The nested-group gallery moves a yellow dot while a green circle remains centered
on a red reference, adds/removes a distant purple dot, and keeps a blue square
fixed. Tests cover Group and VGroup, nested rotation, positive/negative/zero scale,
mutation ordering, empty replacement, copy/restore isolation and frame cleanup.
Existing coordinate-helper tests verify transformed tick/label insertion and
coordinate round trips. Native world-space child coordinates and recursive
point-array transformations still remain incomplete.

Reference: [official Manim family transformation implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).

Local Pyodide playback showed four circles at five seconds with the purple child
present, three at six seconds after removal, and zero at ten seconds. The green
circle remained centered on its red reference. Switching to DOT rendered the
editor flow graph. All 316 Python and 76 Node tests passed.


## Arrangement after rotation and scaling

Group/VGroup arrange now composes each child's uniform scale, angle and center
with the parent's pose on temporary copies. next_to arranges these world-space
copies using the requested direction, buffer and aligned edge. Only the resulting
translations are inverted into parent-local coordinates and applied to live
children, followed by shared pivot compensation and optional centering. The
live parent angle/scale, child identities, callbacks and orientations remain
unchanged, including during .animate position interpolation. All translations
are validated before changing live geometry.

Positive and negative nonzero scales, nested children, screen-space gaps, aligned
edges, center=False first-child preservation, checkpoints and animation samples
have Python coverage. Zero-scale groups remain unsupported because the transform
cannot be inverted. Bounding-box conservatism, text metrics and independent
world-space child-coordinate semantics remain unfinished.

Reference: [official Manim arrange implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).

The local Pyodide gallery rearranged 30-degree shapes into a column with aligned
left edges at four seconds, retained the 0.8 parent scale, restored the diagonal
row at seven seconds, and removed all geometry at nine seconds. Switching to DOT
rendered the editor flow graph. All 320 Python and 76 Node tests passed.


## Group and VGroup grid layout

arrange_in_grid now supports rows/cols inference from child count, alignment
strings or size lists; explicit dimensions; horizontal/vertical buffers; all
eight row/column fill directions; cell_alignment; u/c/d row and l/c/r column
alignments; and explicit row_heights/col_widths with None entries for automatic
world-bounds measurement. Empty cells contribute no geometry. Grids retain the
starting group center and enforce finite inputs, option lengths and a 1000-cell
limit before applying child translations. Zero-scale groups remain unsupported.

Row and grid layouts share temporary world-space pose composition and inverse
translation application. The parent rotation/scale and live child references
remain fixed, supporting animation without extra pose interpolation. Bounds
remain conservative for curves/composite families and incomplete for glyphs;
ordinary geometry-bearing parent layout is now supported as described below;
native world-coordinate child semantics remain unfinished. Rectangle internal grid-line geometry is separate.

Tests independently check all eight fill orders, explicit spacing, center
preservation, inferred and incomplete grids, variable cell dimensions, aligned
edges, nested rotated/negative-scale families, restoration and atomic invalid
options. Frame tests cover animated three-row reflow, column alignment, parent
pose preservation and restored geometry.

Reference: [official Manim arrange_in_grid implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).

Local Pyodide playback showed six shapes in three rows at four seconds, retaining
18-degree orientation and 0.8 scale. The original two-row grid returned at seven
seconds; no circles remained at nine seconds. Switching to DOT rendered the
editor flow graph. All 325 Python and 76 Node tests passed.


## Direct-child layout on ordinary shapes

Row/grid helpers and public arrange/arrange_in_grid now live on Mobject. Group
and VGroup inherit the same methods; ordinary geometry-bearing shapes and empty
containers can arrange direct children. Own geometry is excluded from layout
selection even when split/index/iteration include it. arrange_submobjects is a
dynamic alias of arrange, with .animate support. Rotation/nonzero signed scale,
world-space buffers, row/column options, validation and pivot compensation are
shared with group layout.

With center=False, row layout preserves the first child's world position and the
parent's own outline. Optional centering translates the entire family. Grid
layout preserves the family's initial center, including own geometry in that
center, matching the common family API. Child identities/callbacks, copying and
checkpoints survive layouts. Zero-scale families, conservative path bounds, glyph
metrics and native recursive world-point transformations remain incomplete.

Reference: [official Manim common layout and alias implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/mobject.html).

Tests cover rectangles, circles, VMobject paths and point-free Mobject parents
with positive/negative transforms, own-outline and first-child invariance,
world-space spacing, center preservation, references, copy/restore isolation,
empty families and atomic rejection. The gallery's sampled rectangle corner
stays aligned to its reference throughout grid/row transitions and restoration.

Local Pyodide playback showed four colored child dots in a grid at four seconds,
the restored row at seven seconds, and no rectangle/dots at nine seconds. The
white corner reference remained aligned. Switching to DOT rendered the editor
flow graph. All 328 Python and 76 Node tests passed.


## Standalone editable arrow-tip geometry

ArrowTip is now an abstract VMobject base with geometry-derived tip_point, base,
vector, tip_angle and length properties. Triangular outline/filled classes and
StealthTip construct closed corner paths and use the existing SVG/path/morph
flow. Triangle length/width and angle inputs are validated; a stable trig phase
avoids coincident vertices caused by adding small increments to huge angles.
Triangle bounds are centered in local coordinates. Base sampling uses the
ordered curve-array midpoint, matching native tip anchor semantics, rather than
the runtime's distance-based point_from_proportion. Stealth length uses its
enclosing-triangle factor; its start_angle is stored metadata.

These objects support positive/negative/zero scaling, rotation, own-point APIs,
partial curves, family filtering, layout, callbacks, copying and checkpoints.
They also attach to Line/Arrow as real children; see the integration notes below.
General Arc/Circle tip attachment remains open.

Reference: [official Manim arrow-tip implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/tips.html).

Tests cover constructor styles, tip/base/vector/angle/length, transformed queries,
zero dimensions, abstract/invalid inputs, stable huge-angle construction, editing,
copy/restore, partial paths, family layout and animated marker alignment. Local
Pyodide playback showed a red stealth morph with white tip and purple base markers
at six seconds, restored green triangular geometry and its original anchors at
seven seconds, and no paths/dots at nine seconds. Switching to DOT rendered the
editor flow graph. All 332 Python and 76 Node tests passed.


## Real tips on straight connectors

Line/Arrow implement add_tip (supplied ArrowTip or concrete tip_shape), pop_tips,
has_tip/has_start_tip, get_tip/get_tips and tip/start_tip accessors. Role tags identify
end/start children. Replacement keeps unrelated children; pop_tips returns the
removed objects and restores the full shaft. Logical endpoint queries include the
tip point, while own get_points exposes the trimmed shaft. Tip queries use parent-
local coordinates; compose the parent transform to get scene coordinates.

Arrow defaults to buff=.25, stroke_width=6, tip_length=.35, a filled triangular
head, max_tip_length_to_length_ratio=.25 and max_stroke_width_to_length_ratio=5.
Line defaults to buff=0. Long segments are buffered on both ends; segments no
longer than twice the buffer remain untrimmed. Endpoints/buff reject nonfinite or
non-XY inputs. NumberPlane.get_vector explicitly uses buff=0.

Arrow.scale compensates tip scale about its point by default; scale_tips=True
retains uniform family scaling. Parent-group scaling follows ordinary family
semantics. Endpoint edits reorient live tips and retain the parent's rotation/scale.
Collapsed parents cannot add tips. Snapshot serialization and capture recompute
shaft bases from the actual sampled child geometry. Tip roles follow aligned
target slots during morphing. The SVG renderer paints the shaft and real child
outlines without adding an implicit head; older packets still use the legacy head.

The gallery exercises two heads, fixed-size scaling, endpoint edits, replacing the
heads with a stealth tip, restoration and cleanup. General curved-tip APIs,
Arrow partial curves and cross-type path morphs,
and native world-coordinate child semantics remain open.

Reference: [Manim TipableVMobject API](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.arc.TipableVMobject.html).


Verification: all 335 Python and 77 Node tests passed. Local Pyodide playback
showed the replaced stealth tip at six seconds, the original two tips and white
endpoint marker at eight seconds, and no lines/paths/dots at ten seconds.
Switching to DOT rendered the Editor → Render → Preview graph.


## Circular and square arrow tips

ArrowCircleTip/ArrowCircleFilledTip and ArrowSquareTip/ArrowSquareFilledTip extend
ArrowTip with editable closed outlines. Circle tips use the existing eight-cubic
circle approximation; square tips use four corner segments. Both shapes center
their bounds locally. Circle length is its diameter; square length input is its
side, while the inherited length property measures its diagonal anchor span.
Circle start_angle sets the first anchor and is normalized before curve generation
so huge finite angles still produce distinct points. Square start_angle is stored
metadata and leaves the native default corner order unchanged.

Outline defaults are fill_opacity=0/stroke_width=3; filled defaults are 1/0 and
remain overridable. Constructors reject negative/nonfinite dimensions and invalid
angles; zero dimensions produce collapsed editable paths. The tip attachment,
sampled shaft derivation and ordinary VMobject morph pipeline require no special
renderer branches for these shapes. Native Circle/Square class inheritance and
the broader native API remain unfinished.

Reference: [Manim circle and square tip constructors](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/tips.html).

`examples/round_square_tips_scene.py` uses four different tips on two arrows,
tracks their endpoint markers through rotation/scaling and endpoint edits,
restores original geometry and removes the whole family. Tests cover shape and
style defaults, anchor queries, closed paths, transformed lengths, editing,
partial curves, copy/restore, validation, both-end attachment and per-frame shaft
alignment.


Verification: all 338 Python and 77 Node tests passed. Local Pyodide playback
showed two trimmed shafts, four styled tip outlines and two endpoint markers
at six seconds, restored geometry at seven seconds, and no geometry at nine
seconds. Switching to DOT rendered the Editor → Render → Preview graph.


## Double-ended straight arrows

DoubleArrow extends Arrow, adds a start tip after constructing the end tip, and
uses the existing two-role shaft geometry. tip_shape_start defaults to
ArrowTriangleFilledTip independently of the end shape. tip_shape_end overrides
tip_shape when both are provided; other positional/keyword arguments forward to
Arrow. No new frame or renderer type is introduced.

The class inherits endpoint buffering and queries, both-end tip management,
length/stroke caps, fixed-size or uniform tip scaling, rotation and direct or
animated endpoint edits. Copying yields independent tip children. Restore
animation preserves existing matching tip identities; pop_tips returns both
original tip objects and restores the full shaft. Native world-coordinate child
semantics and straight Arrow partial-path/cross-type morph behavior
remain open.

Reference: [Manim DoubleArrow implementation](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/line.html).

Tests verify default tips/buffer, separate shape configuration and precedence,
validation, negative/positive scaling, animated endpoint markers, per-frame shaft
bases, checkpoint geometry, child identity retention, copying and removal/reuse.
The gallery contains a default triangular DoubleArrow and a square/circular
DoubleArrow, with four live endpoint markers, pose and endpoint animations,
restoration and final cleanup.


Verification: all 341 Python and 77 Node tests passed. Local Pyodide playback
showed two shafts, four tip paths and four endpoint markers at six seconds,
restored horizontal geometry at seven seconds, and no geometry at nine seconds.
Switching to DOT rendered the Editor → Render → Preview graph.


## Tangent-aligned curved arrows

CurvedArrow/CurvedDoubleArrow extend ArcBetweenPoints and reuse Line's tip APIs.
They materialize the endpoint arc as world-space cubic geometry before attaching
real child tips. Tip orientation uses endpoint minus adjacent handle, including
reverse direction at the start. Signed angles/radii, straight zero-angle paths
and coincident endpoints follow the existing endpoint-arc constructor. Tip length
defaults to .35 without straight Arrow's size/stroke caps. CurvedDoubleArrow uses
independent start/end shapes with the same precedence as DoubleArrow.

Raw curves retain the logical full path. _refresh_tip_shafts derives both local
base coordinates and shaft_curves via a 2D similarity mapping from raw endpoints
to current sampled tip bases. _path_curves and the SVG cubic renderer consume
shaft_curves; logical endpoint queries compose actual child tip points with the
parent transform. pop_tips restores the untrimmed path. Path alignment uses raw
curves to avoid fitting an already trimmed shaft a second time when curve counts
differ. Sample capture then fits the aligned interpolated shaft to its live tips.

Curved endpoint fitting transforms the entire family about the old start, then
moves it to the requested start. Scaling includes the tips, unlike standalone
straight Arrow's fixed-size default. Arc center queries retain their stored local
center through these transforms. Fitting cannot expand a collapsed curve.
Ordinary transforms, same/different-count curved morphs, copying, callbacks and
restoration use the existing family flow. Native world-coordinate children,
general Arc/Circle tip APIs, arbitrary 3D curves, native mutable point semantics
and general tip-bearing partial-path behavior remain unfinished.

Reference: [Manim curved arrows and tip placement](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html).

Tests cover tangent directions, positive/negative/zero sweeps, zero-length
validation, both-end shapes, shaft bases, signed scaling, endpoint/center edits,
copy/checkpoints, removal, unequal-count morphs and gallery endpoint tracking.


Verification: all 344 Python and 78 Node tests passed. Local Pyodide playback
showed two curved shafts, three tip paths and four endpoint markers at six
seconds, restored geometry at seven seconds, and no geometry at nine seconds.
Switching to DOT rendered the Editor → Render → Preview graph. Curve fitting
normalizes offsets before mapping, avoiding reciprocal overflow for tiny spans.


## Tip styles and detached factories

Line accepts tip_length and a copied tip_style mapping. Arrow passes its requested
length through Line; CurvedArrow initializes the same style mapping before
attaching tips. Straight/curved double-arrow classes inherit this behavior.
get_unpositioned_tip constructs an independent shape with default fill/stroke
colors from the connector stroke, then applies tip_style overrides. Existing
constructor validation handles styles and rejects unsupported options.

For exactly ArrowTriangleFilledTip, generated width is explicit tip_width or
get_default_tip_length; a width in tip_style takes precedence. Other shapes keep
their shape-specific dimensions. Explicit length/width validate as finite,
nonnegative real values. This also corrects width capping for short default Arrow
heads; width and length now share the default length cap.

create_tip makes a tip, compensates parent scale for requested world dimensions,
and positions it without attaching or assigning a role. position_tip orients a
supplied ArrowTip in parent-local coordinates and also leaves it detached.
add_tip reuses these helpers; supplied tip objects retain their own style/size.
Factories retain shaft geometry and existing children. Positioned creation rejects
collapsed parents; unpositioned creation remains available. get_tip now returns
the first attached end/start tip, while tip/start_tip properties stay role-specific.

Reference: [Manim tip creation and style precedence](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html).

Tests cover copied dictionaries, independent colors/opacities, width/style
precedence, default width caps, detached placement and attachment, transformed
straight/curved factories, start-only tip queries, validation and failure without
live mutation. The gallery replaces a styled tip with a wider detached factory
tip, recolors it independently, restores the original tip and removes both arrows.
General TipableVMobject inheritance, generic Arc/Circle attachment, 3D positioning
and native world-coordinate children remain unfinished.


Verification: all 347 Python and 78 Node tests passed. Local Pyodide playback
showed the wider green tip with white border at six seconds, restored red fill
(.4 opacity) and yellow border at seven seconds, and no geometry at nine seconds.
The curved arrow retained yellow fills (.5 opacity) and purple outlines independently
of its green shaft. Switching to DOT rendered the Editor → Render → Preview graph.


Try **Attach tips to arcs and circles** (`examples/generic_tips_scene.py`).
TipableVMobject now shares the XY tip factories and management API across Line,
Arc, Circle and their subclasses. Open paths fit their cubic shaft endpoints to
actual tip bases; closed circles retain their complete outline and place tips at
the shared start/end anchor. Attachment preserves the path's existing pose.
Logical endpoint queries use tip points, while own-point queries use the fitted
shaft. Ordinary family transforms, endpoint fitting, copying and restoration
include attached tips. TipableVMobject can also hold explicitly constructed cubic
or corner paths. Empty paths reject positioned tips. normal_vector must be finite
and perpendicular to the XY plane. Native world-coordinate children, general
mutable-tip path semantics and arbitrary 3D remain unfinished.


Verification: all 350 Python and 78 Node tests passed. Local Pyodide playback
rendered the open arc with two tangent tips and the closed circle with a stealth
tip at six seconds, restored the saved pose at seven seconds and removed all
geometry at nine seconds. Switching to DOT rendered Editor → Render → Preview.


Try **Construct circles through three points** (`examples/circle_construction_scene.py`).
`Circle.from_three_points(p1, p2, p3, **style)` constructs an XY circumcircle;
points must be finite, distinct and noncollinear. Normalizing the chord calculation
supports both very small and very large finite geometry. Nonfinite results and
3D point sets fail explicitly. `Circle.point_at_angle(angle)` wraps any finite
angle into a path proportion, so its result follows rotation, signed scaling,
translation and edited outline geometry; the angle refers to path traversal,
not an absolute screen direction. Circle now inherits Arc and accepts arc_center,
with get_arc_center/move_arc_center_to available to Circle and Ellipse. Radius
None selects the existing unit default; invalid radii now fail at construction.
The gallery retains the three original points while a boundary marker follows
the moving circle, then restores the circle and removes the scene.

Reference: [Manim Circle construction and point queries](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.arc.Circle.html).
Circle surround/stretch behavior, native world-coordinate child semantics and
3D circumcircles remain unfinished.


Verification: all 353 Python and 78 Node tests passed. Local Pyodide playback
showed the red boundary marker following the rotated/scaled translated circle
at six seconds, five circles after restoration at seven seconds and no remaining
geometry at nine seconds. Switching to DOT rendered Editor → Render → Preview.


Try **Surround moving shapes** (`examples/surround_scene.py`). Mobject now provides
`length_over_dim`, `rescale_to_fit`, `scale_to_fit_width`, `scale_to_fit_height`
and `replace` for uniform XY fitting. The chosen dimension uses current family
bounds, including rotation and children; uniform fitting preserves aspect ratio,
style and child identities. `replace` fits the chosen dimension and centers the
existing object on its target without changing that target. These operations also
work in animate chains. Fitting an already zero-size dimension is a no-op, following
Manim's rescale behavior. Lengths must be finite and nonnegative.

`Circle.surround(target, buffer_factor=1.2)` centers the existing circle on the
target and sets its width to the target's bounding-box diagonal times the factor.
This handles both horizontal and vertical lines without collapsing the circle
before the final fit. A factor below one makes a smaller outline. An updater can
repeat surround as the target moves, rotates or scales. Bounds remain conservative
for rotated families and cubic handles. Nonuniform stretch=True and dimensions
outside XY remain explicitly unsupported; full stretching is still implementation
work. Empty targets and invalid values fail before mutation.

Reference: [Manim size fitting and replacement](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html),
[Circle surround](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.arc.Circle.html).


Verification: all 356 Python and 78 Node tests passed. Local Pyodide playback
showed the yellow circle following the rotated, resized and translated rectangle
at six seconds, restored them at seven seconds and left only the black canvas
background at nine seconds. Switching to DOT rendered Editor → Render → Preview.
