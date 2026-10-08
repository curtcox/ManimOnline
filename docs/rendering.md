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
smoothing and full point-array APIs remain gaps. Separate contours are described below.

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
smoothing and general point-array APIs remain open.

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
broader partial-creation animations, smoothing and glyph outlines
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
