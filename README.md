# [ManimOnline](https://curtcox.github.io/ManimOnline)

A web-based editor that supports both Graphviz DOT language diagrams and Manim Python animations, with automatic detection and appropriate rendering.

## Features

- **Graphviz DOT Support**: Full support for Graphviz DOT language diagrams
- **Manim-lite animations**: In-browser Python execution with SVG frame playback, play/pause, replay, and seeking
- **Examples**: Load supported animation examples or a Graphviz diagram directly into the editor
- **Auto-Detection**: Automatically detects whether input is DOT or Manim Python
- **Renderer selection**: Choose Auto, Manim, or Graphviz when detection is ambiguous
- **URL Sharing**: Share diagrams via URL parameters
- **Export**: Download diagrams as SVG or PNG

## Usage

Visit the deployed site and start typing:
- For Graphviz: Write DOT language code (e.g., `digraph { a -> b }`)
- For Manim: Write a `Scene` subclass with `from manim import *` (see the supported subset below).

Choose an **Example**, then select **Load example** to replace the editor source
and preview it. You can edit the loaded code, select a scene, seek, and export
as usual. Loading clears any earlier scene selection and URL input override.
If you edit while an example is loading, your newer edits are kept. Loading
errors leave the current code intact. The gallery uses bundled supported scenes;
it does not imply support for every Manim API in the broader example documents.

The **Renderer** selector defaults to Auto. It ignores strings and comments when
detecting source, so diagram labels and Python docstrings do not choose the
renderer. Choose Manim or Graphviz to override detection; the choice stays in the
URL and shared links. Choose Auto to remove the override. Loading an example
also restores Auto. Detection updates after 300 ms of quiet; rendering starts
after one second. Changing the renderer or pressing Enter in the scene field
renders immediately and cancels scheduled work for earlier edits. **Render
animation** also starts immediately, including a retry after an error or timeout.
**Cancel render** stops active Manim work without changing the source. It is
available during Python loading, execution, and formula preparation; the last
completed preview remains paused. Editing still starts a new render after the
usual delay.

On screens up to 760 pixels wide, the toolbar, code editor, and preview stack
vertically. Code wraps to fit the editor; **Hide code** gives the preview more
space, and **Show code** restores editing. Controls wrap and scroll on short
screens, and playback controls use larger touch targets. Desktop retains the
resizable split view. Narrow-screen browser checks cover playback, seeking,
editor visibility, and switching to DOT; native mobile keyboard/device testing
is still needed.

## Development

This is a static site that can be served directly. To run locally:

```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx serve .
```

Then open `http://localhost:8000` in your browser.

## Agent orientation

- [AGENTS.md](AGENTS.md): project map and working guidance.
- [Rendering roadmap](docs/rendering.md): current limitations and next milestones.
- [Minimal scene](examples/minimal_scene.py): baseline animation input.
- [Multiple scenes](examples/multiple_scenes.py): scene selection, scale, and rotation.
- [Creation and rotation](examples/creation_and_rotation.py): outline drawing and a circular orbit.
- [Layout scene](examples/layout_scene.py): shape spacing and animated row-to-column arrangement.
- [Staggered scene](examples/staggered_scene.py): delayed reveals, overlapping movement, and staggered fades.
- [Path scene](examples/path_scene.py): motion along transformed circles, polygon outlines, and lines.
- [Arc scene](examples/arc_scene.py): open circular paths and clockwise/counterclockwise motion.
- [Growth scene](examples/growth_scene.py): growth from a point, group growth, and staggered shrinking.
- [Shape morph scene](examples/shape_morph_scene.py): deform primitive outlines, restore a circle, and finish as a curve.
- [Morph scene](examples/morph_scene.py): align unequal corner/curve counts, restore, and close an outline.
- [Bezier scene](examples/bezier_scene.py): trace, follow, deform, and restore cubic curves and mixed paths.
- [Corner paths](examples/corner_path_scene.py): trace, follow, and deform a connected path.
- [Scene lifecycle](examples/lifecycle_scene.py): setup-created objects, scene time, and teardown animation.
- [Foreground scene](examples/foreground_scene.py): keep a grouped overlay above later additions and release it.
- [Scene order](examples/order_scene.py): reorder whole groups, clear the display, and reuse objects.
- [Layer scene](examples/layer_scene.py): animated depth changes across transformed groups.
- [Style scene](examples/style_scene.py): independent fill/outline colors and group opacity changes.
- [Restore scene](examples/restore_scene.py): saved geometry/styles, animated restoration, and recovery from zero size.
- [Indicate scene](examples/indicate_scene.py): temporary highlights and staggered emphasis.
- [Copy scene](examples/copy_scene.py): copy transforms, retained originals, and target cleanup.
- [Math scene](examples/math_scene.py): vector formulas, highlights, and formula crossfades.
- [Connector scene](examples/connector_scene.py): endpoint motion on a rotated arrow and checkpoint restoration.

## Supported browser animation subset

Python runs in a Web Worker using Pyodide 0.27.0. The browser loads Python on
first use, so the first render needs an internet connection. This is a small
Manim-like runtime, **not the full Manim Community engine**.

- Shapes: `Circle`, `Ellipse`, `Arc`, `Sector`, `AnnularSector`, `Annulus`, `CubicBezier`, `VMobject`, `Dot`, `Square`, `Rectangle`, `RoundedRectangle`, `Line`, `Arrow`, `Triangle`, `Polygon`,
  `Text`, `MathTex`, and `VGroup`.
- Scene operations: `add`, `remove`, `play`, and `wait`.
- Animations: `Create`, `Uncreate`, `Write`, `FadeIn`, `FadeOut`, `GrowFromCenter`,
  `GrowFromPoint`, `ShrinkToCenter`, `Rotate`,
  `Rotating`, `MoveAlongPath`, `AnimationGroup`, `LaggedStart`, `Succession`, `Transform`, and
  `ReplacementTransform`, `TransformFromCopy`, `Restore`, and `Indicate`; chained `.animate.shift()`, `.move_to()`,
  `.set_color()`, `.set_fill()`, `.set_stroke()`, `.set_opacity()`, `.scale()`, `.rotate()`,
  `.next_to()`, `.arrange()`, and `.restore()`.
- Connectors: `Line` and `Arrow` support `get_start()`, `get_end()`,
  `get_start_and_end()`, `get_vector()`, `get_length()`, `get_unit_vector()`,
  `get_angle()`, and direct or animated `put_start_and_end_on(start, end)`.
- Layout: `move_to` centers geometry on a point or another object; `next_to`
  positions shapes with `direction`, `buff`, and `aligned_edge`; `VGroup.arrange`
  creates rows or columns with optional `center=False`.
- Geometry: uniform scaling, 2D rotation in radians, optional `about_point`,
  `get_center()`, and `PI`, `TAU`, and `DEGREES` constants.
- Paths: `point_from_proportion(alpha)` for circles, arcs, lines, polygons, squares,
  rectangles, triangles, and VMobject corner/cubic paths, including their 2D geometry transforms.
- Timing: `run_time`, `linear`/`smooth` rate functions, simultaneous animations,
  and nested animation groups with staggered starts.
- Directions support vector addition/subtraction and scalar multiplication,
  such as `RIGHT * 2`.

`Create` progressively traces primitive shape outlines and fades in their fill;
`Uncreate` reverses that draw and removes the object. Groups reveal all children
simultaneously. Text creation and `Write` use fades because glyph paths are not
available in this runtime. MathTex creation also uses fades. Arrow shafts and heads reveal together. Transforms
interpolate matching geometry and align supported primitive/corner/cubic/polygon
outlines for morphing. Text, arrow, and other unsupported outline combinations crossfade.
`TransformFromCopy(source, target)` animates the target from a snapshot of the
source while preserving the source. Add the source first to keep it visible;
only the target is automatically added. Both are snapshotted at playback start.
The target retains its identity, children, and saved state for later animations.
An already visible target is animated in place. Sources may animate independently;
targets must obey the usual one-animation-per-object and group-family rules.
While tracing, stroke widths scale with the shape and preview size so the
drawn fraction stays accurate; completed objects use fixed-width strokes.
Leave the Scene field empty to render the first scene defined in the source,
or enter a class name to choose another. Successful renders suggest the scene
names in that file. Press Enter to render immediately; editing the field also
rerenders after a short delay. The selected name is preserved in the URL as
`?scene=ClassName` and in shared links. If the class is removed or renamed, clear
or update the field to resolve the selection error.

Scaling and rotation use the object's center by default. Group centers use
child bounds; text is center anchored without full font metrics. Animation
chains interpolate transform values, and an external rotation pivot moves the
center between endpoints rather than following a circular arc. These are
preview semantics, not full Manim geometry behavior.

Use `Rotate(object, angle=PI, about_point=ORIGIN)` for rigid circular motion
around an external pivot, or omit `about_point` to rotate around the object's
center. `Rotating` defaults to a full turn over five seconds at a constant rate;
`Rotate` defaults to a half turn over one second with smooth easing. Both accept
`angle`, `about_point`, `run_time`, and `rate_func`. `OUT` rotates counterclockwise
and `IN` reverses it; other axes are unsupported. Unlike `.animate.rotate()`,
these animations sample the circular trajectory at each frame.

`MathTex(r"\frac{a}{b}", font_size=48, color=BLUE)` renders formulas as vector
paths through MathJax 3.2.2, loaded on first math use. Multiple string arguments
are joined with `arg_separator=' '`. Fractions, integrals, sums, roots, and AMS
math are supported; formulas use display math. Scale, rotation, colors, fades,
groups, and highlights work normally. Transforms to another formula crossfade.
SVG exports contain the formula paths and need no math fonts or library.
Creation and writing fade the entire expression. Glyph selection, substring
color maps, custom templates/macros/packages, `Tex`, and matching-symbol
transforms are not implemented. Python layout uses the formula anchor, without
glyph bounds. First math use needs internet access; limits are 4096 characters
per formula, 64 distinct formulas, and 2 MiB of generated math SVG per preview.
Characters requiring browser font fallback rather than vector glyphs show an
unsupported-glyph error.

Connector endpoint queries include the line's own scale, rotation, and position.
`put_start_and_end_on` accepts finite XY points and preserves styles and saved
states. Zero-length and zero-scale connectors can be expanded again. Queries on
group children use parent-local coordinates. Curved connectors, boundary
attachments, and line buffers remain unsupported; arrows use shaft endpoints.

`Dot` is a filled circle with radius 0.08 and no outline by default. Layout
uses bounding boxes in the XY plane and a default gap of 0.25 units. Text
bounds use only its center anchor, so layout does not account for text width
or height. Rotated polygon/line bounds are conservative; arrowheads and stroke
thickness do not contribute to spacing. Arrange groups before scaling or
rotating them, then apply the group transform. Group children use local
coordinates; placing a child independently does not resolve its parent's
transforms. Animated layouts interpolate child positions between arrangements.

`AnimationGroup` starts its children together by default; `LaggedStart` defaults
to `lag_ratio=0.05`. Each next child starts after the previous child's duration
times `lag_ratio`. The natural group duration is the latest child end time.
Group `run_time` (or `play(..., run_time=...)`) rescales the timeline while
preserving overlap. Group easing changes timeline progress; child easing changes
each animation's progress. Groups may nest, and `VGroup` is iterable for building
animation lists. Use independent objects: repeated objects, parent/child overlap,
and animating a child inside a scene-added group are unsupported. Animate the
whole added group or keep its children as separate scene objects.

`Succession` runs consecutive, non-overlapping stages (`lag_ratio=1`). Its
duration is the sum of its children; `run_time` rescales that timeline. Repeated
objects are allowed across stages. Each stage begins from the previous stage's
finished geometry and visibility, so two `Rotate` steps accumulate, a replacement
can be animated next, and future introductions stay hidden until their stage.
Nested sequences and independent groups are supported. Relative `.animate`
method chains resolve against the object and layout references at stage start;
explicit `Transform` targets remain snapshots made when constructed.

Sequences prepare against a copied scene and commit live changes in stage order
at completion. A sequence cannot share animated objects with a simultaneous
animation outside it, and each parallel stage still requires independent object
families. Root drawing order stays fixed while sampling one play call; removal
and reintroduction change live order at completion. Read-only path/copy references
outside the sequence are snapshotted during preparation, so they do not track
concurrent animations. Overlapping `Succession` stages and automatic scene-family
restructuring remain unsupported. Completed groups hold their terminal state
even when a rate function returns to zero.

`MoveAlongPath(object, path)` moves the object's center along a path without
turning it to face the direction of travel. It defaults to one second with
smooth easing; use `rate_func=linear` for linear path proportion. Paths are snapshotted
at animation start. Circles use exact circular sampling from the positive X
axis counterclockwise; polygon outlines follow their vertex order and close
back to the first vertex. Square/rectangle paths start at the upper right
corner; triangles start at their top vertex. Straight edges are sampled by
distance, so longer edges take proportionally longer. Path sampling is limited
to the XY plane; connected cubic curves are described below. Groups, text,
arrowheads and live path updates are unsupported. Separate contours are sampled
without counting the gap between them; motion jumps across that gap.

`Arc(radius=1, start_angle=0, angle=PI/2, arc_center=ORIGIN)` draws an open
circular arc. Angles are in radians; positive sweeps go counterclockwise and
negative sweeps clockwise, up to one full turn. Arcs work with `Create`,
`Uncreate`, transforms, layout, and `MoveAlongPath`. `get_arc_center()` returns
the underlying circle center; `move_arc_center_to(point)` moves that center and
also works in animate chains. `move_to` and default scale/rotation use the
visible bounding-box center. Arc path sampling follows its starting angle and
sweep. Fill closes the endpoints with a chord; sectors, 3D arcs, multiple turns,
and `num_components` are unsupported.

`GrowFromCenter(object)` expands geometry from its bounding-box center;
`GrowFromPoint(object, point)` expands from a fixed XY point while moving toward
its original center. Both restore the original size, rotation, style, and
position at completion. `ShrinkToCenter(object)` contracts around its center
and leaves the object in the scene at zero scale; use `remover=True` to remove
it at completion. These animations work on
whole groups and accept `run_time` and `rate_func`, defaulting to one second
with smooth easing. Growth centers are resolved when playback begins. Point
colors, curved growth trajectories, and 3D growth are unsupported. Text uses
its anchor as its center; normal preview stroke-width behavior still applies.

Shapes accept `fill_color`, `stroke_color`, and `stroke_opacity` in addition to
`color`, `fill_opacity`, and `stroke_width`. `set_fill(color, opacity)` changes
only the fill; `set_stroke(color, width, opacity)` changes only the outline.
`set_color(color)` sets both colors without changing their opacity.
`set_opacity(value)` sets both fill and stroke opacity, making an unfilled
shape filled as well. Setters recurse into group children by default;
`family=False` changes only that object's style. Group container styles do not
override children when rendering. All four setters work in animate chains.
Opacity must be between zero and one; stroke widths must be nonnegative and
finite. Fades multiply existing style opacity. Text has no outline by default
but supports `set_stroke`; arrows use stroke styling for shaft and open head.
Color interpolation supports six-digit hex strings; other CSS colors switch
at the animation endpoint. Gradients and background strokes are unsupported.

`object.save_state()` keeps one checkpoint of geometry, styles, and group
children. A later save replaces it. `object.restore()` returns to it immediately;
`Restore(object)` or `object.animate.restore()` animates the return using normal
transform timing. A saved state survives changes to the object's shape type,
and can restore size after `ShrinkToCenter`. Restore animations snapshot the
checkpoint when constructed; restoring without one raises an error. The root
object keeps its identity, while group children are copied, as with transforms.
Keep working through the restored group instead of retaining old child references.
Checkpoints do not capture scene membership or camera state and are excluded
from frame output and SVG export. Removed objects can be reintroduced by a
Restore animation; a direct restore does not add them to the scene.

`Indicate(object, scale_factor=1.2, color=YELLOW)` temporarily scales an object
around its center and recolors both fill and stroke. It defaults to one second
with `there_and_back` easing: the effect peaks halfway through, then returns.
Fill/stroke opacity and rotation are preserved. Whole groups and text are
supported, including staggered animation groups. The live object, its children,
and saved checkpoint remain unchanged; the original appearance is always held
after the effect ends. Custom `rate_func` controls intermediate progress, but
an easing that does not return to zero can jump back at completion. The exported
`there_and_back` uses this runtime's cubic smooth curve; ordinary transforms
still commit their destination at completion when using this rate function.
Scale factors must be finite and nonnegative. Preview bounds and color
interpolation limitations apply to this effect as well.

Animation previews run at
15 frames per second and are limited to 60 seconds, with a 90-second deadline
for loading and execution. Editing or Cancel render terminates active Python computation. Choose SVG or PNG
under Frame format, then Download to save the current frame. PNG pauses playback
at the displayed frame and exports an 800 × 450 image with a black background.
These are still images, not video exports. SVG retains vector formula paths;
PNG includes those paths and the browser's rendered text.

Full LaTeX documents, 3D, updaters, full NumPy integration, and MP4 export
are not implemented. The broader examples directory includes APIs
outside this subset. Unsupported operations report Python errors.

Objects accept a finite numeric `z_index` (default 0). `set_z_index(value,
family=True)` applies it to the object and its descendants; `family=False`
changes only the object's own value. Drawable shapes are sorted across all group
boundaries by increasing depth, so higher values appear in front. Equal depths
keep scene/family insertion order. Group containers have no drawable geometry;
changing only a container's depth does not change its children. Animated depth
changes, copies, transforms, and Restore preserve these values. SVG/PNG snapshots
use the same paint order as the displayed frame. This follows the
[Manim depth-setting API](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html#manim.mobject.mobject.Mobject.set_z_index).
`Scene.bring_to_front(*objects)` and `bring_to_back(*objects)` reorder whole
scene roots, including entire groups, in argument order and add absent roots.
Repeated arguments appear once. They keep geometry and depth unchanged, so
`z_index` takes priority over insertion order. `Scene.clear()` removes displayed
objects without changing their state or deleting earlier frames; the same objects
can be added or animated again. Ordering a child of an added group or a group
containing independently added children requires family restructuring and reports
an explicit error before changing the scene. Broader scene-family restructuring
remains unsupported.

`add_foreground_mobject(object)` and `add_foreground_mobjects(*objects)` add whole
roots to `foreground_mobjects` and the scene. Foreground roots stay after ordinary
roots as later objects and animations are added, so they cover equal-depth objects.
Re-adding foreground roots moves them to the end of the foreground list, in argument
order; duplicates appear once. Numeric `z_index` still takes priority, including
across children of foreground groups. `remove_foreground_mobject(object)` and the
plural form release the foreground designation while keeping the object visible.
Later additions can then cover it. `remove`, fade/removal animations, and `clear`
remove foreground membership too. `bring_to_front` preserves membership;
`bring_to_back` releases it. Child/group restructuring is rejected atomically.
See the [Manim Scene API](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html).

Scenes may override `setup()` and `tear_down()`. The runtime calls setup before
construct and teardown afterward; all three hooks can add objects, play
animations, and wait. Inherited hooks work normally. A hook error stops rendering
and propagates to the editor; later hooks are not run. The final seekable frame
captures the state after teardown.

Read-only `Scene.time` reports elapsed sampled animation time in seconds. Waits
and the longest parallel animation advance it at 15 fps; durations round up to
whole frames. Clearing the display does not reset it, and the final still frame
does not advance it. Time is independent of Python execution/loading and browser
playback or seeking. The hook order and time concept follow the
[Manim Scene API](https://docs.manim.community/en/stable/_modules/manim/scene/scene.html).

`VMobject()` supports connected and disconnected XY paths. Build it with
`set_points_as_corners(points)`, extend it with `add_points_as_corners(points)` or
`add_line_to(point)`, and reverse it with `reverse_direction()`. These methods
also work in animate chains. Points are local coordinates and must be finite;
repeat the first point at the end to close the outline. Empty paths render no
geometry, and endpoint queries require at least one point.

Corner paths support Create/Uncreate, styles, layout, group/depth ordering,
transforms, checkpoints, `get_start()`/`get_end()`, and `MoveAlongPath` sampled
by distance along straight segments. Equal-count point lists interpolate;
unequal-count corner paths and polygons align through cubic subdivision before
interpolation. Smoothing and general point-array operations remain unsupported. Separate-contour
construction and alignment are described below. This uses the
[Manim corner-path API](https://docs.manim.community/en/stable/reference/manim.mobject.types.vectorized_mobject.VMobject.html?highlight=corner)
with a straight-segment SVG representation.

## Offline use

On HTTPS or localhost, the site saves the editor, supported examples, Python
runtime, and MathTex library. Stay connected until the toolbar says **Ready
offline**. Then reload the same site to edit and render DOT or supported Manim
scenes, select gallery examples, and export frames without a connection.
Preparation downloads the runtime even if you are editing DOT. Browser storage
limits or a failed CDN request can prevent setup; use **Retry offline setup**
after reconnecting. Browser storage may be cleared or evicted later.

Only the listed application assets are cached. External source links, URL
shortening, and arbitrary Python packages still need a connection. Source links
are generated locally and use compression when available. A first-ever visit without a connection cannot
load the site; connect for the initial setup. If saved files are incomplete on
an offline reload, the service worker shows a recovery page.

New versions show **Update and reload** once their files are saved. Updates wait
for that action or for old tabs to close. Applying an update reloads other open
tabs too; each tab preserves its latest source and scene selection in its URL
before reloading. Maintainers must bump the version in
`offline-assets.js` when changing a cached local file. The pinned Python assets
follow the [Pyodide deployment manifest](https://pyodide.org/en/0.27.0/usage/downloading-and-deploying.html).

## Sharing scenes

**Share** immediately selects a source link for copying. It contains the current
code, selected scene, renderer override, and DOT engine/format when applicable.
Source links use compression when available and work without a shortening
service. Old `raw`, `compressed`, or external-source parameters are replaced,
so a reload uses the latest edits. Changing source or rendering options clears
the displayed link to avoid copying an outdated version.

**Shorten link** optionally sends that captured source URL through the existing
AllOrigins/is.gd services. If the request fails, stalls for ten seconds, or
returns an invalid link, the source link remains available. Editing cancels
pending shortening and ignores its later response. Tests simulate service
success/failure; live shortening-service availability is not guaranteed.

## Verification

No dependency installation is needed for the tests:

```sh
python3 -m unittest discover -s tests -v
node --test tests/*.test.js
```

Serve the site locally to check actual Pyodide loading and browser playback.
Check the default animation, replay/seek, scene selection and URL reload,
animated scale/rotation, outline drawing and erasure, an orbit, a source edit,
invalid Python, and
switching to `digraph { a -> b }`. These unit tests cover the compatibility
runtime and worker lifecycle; they do not substitute for browser checks.

## Credits

- Based on [GraphvizOnline](https://github.com/dreampuf/GraphvizOnline) by Dreampuf (BSD-3-Clause)
- Uses [viz.js](https://github.com/mdaines/viz.js) for Graphviz rendering
- Uses [Pyodide](https://pyodide.org/) for browser Python execution
- Uses [ACE Editor](https://ace.c9.io/) for code editing
- Uses [svg-pan-zoom](https://github.com/ariutta/svg-pan-zoom) for SVG interaction

## License

BSD-3-Clause (see LICENSE-graphvizonline for GraphvizOnline attribution)


### Cubic Bezier paths

`CubicBezier(start_anchor, start_handle, end_handle, end_anchor, **style)` creates
an open cubic curve. Add a cubic segment to a VMobject's existing endpoint with
`add_cubic_bezier_curve_to(handle1, handle2, anchor)`. Start an empty VMobject with
`set_points_as_corners([start])` first. Earlier corners become straight cubic
segments when a curve is appended. Later `add_line_to`/`add_points_as_corners`
continue the path with straight segments. `set_points_as_corners` replaces the
whole path, and `reverse_direction` reverses segment order and control handles.
Coordinates must be finite and in the XY plane; invalid appends preserve the path.

Curves render as SVG cubic commands with Create/Uncreate, styles, group transforms,
copy/checkpoints, Restore, and MoveAlongPath. Transform interpolates anchors and handles. Unequal segment counts and
corner/cubic/polygon path combinations align through subdivision as described below. Sampling uses the cubic parameter within each segment. For several
segments, their relative durations use lengths estimated with 20 intervals per
segment. This is approximate and does not produce constant speed within a curve.
Geometry bounds and transform pivots enclose anchors and handles, rather than
measuring the visible curve's exact extrema. Disconnected subpaths, arbitrary shape
alignment, smoothing, and the rest of VMobject's point-array API remain unsupported.
See [Manim CubicBezier](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.arc.CubicBezier.html)
and [path sampling](https://docs.manim.community/en/stable/_modules/manim/mobject/types/vectorized_mobject.html).


### Path alignment during transforms

Transform, Restore, ReplacementTransform, TransformFromCopy, and animate chains
can morph connected corner, cubic, and polygon paths with unequal segment counts.
Straight edges become cubic segments, and polygons include their closing edge.
The shorter segment list is subdivided evenly across its existing segments until
both lists match. De Casteljau splitting preserves the original curve and every
join; alignment snapshots keep the original geometry pivots, scale, rotation,
and position. The displayed frame then interpolates paired anchors, handles, and
styles. Both closed endpoints produce a closed SVG stroke with its usual joins.

Alignment leaves the live source and target unchanged until normal animation
completion. Transform finishes with the target's original geometry representation
and preserves the source checkpoint. A one-point path can grow into a segment;
empty paths still fade because they have no anchor to align. Correspondence follows
path order; the runtime does not optimize point matching or winding direction.
Disconnected subpaths, arrow outlines, and nested group-family
alignment remain open. This follows the curve-subdivision concept in
[Manim align_points](https://docs.manim.community/en/stable/reference/manim.mobject.types.vectorized_mobject.VMobject.html#manim.mobject.types.vectorized_mobject.VMobject.align_points).


### Primitive outline morphing

Circle, Ellipse, Arc, Square, Rectangle, Triangle, and Line can morph into each other and
into supported corner/cubic/polygon paths. Straight outlines convert exactly to
cubic segments. Circles and arcs use tangent-matched cubic segments spanning at
most 45 degrees, with exact anchors and closure for full turns. Circular geometry
is slightly approximate during these morphs; static shapes, path sampling, and
same-type primitive transforms retain their previous analytical behavior.
Tests sample the circular approximation with radial error below 0.0005% of radius.

The conversion keeps original layout/transform pivots, positions, styles, depth,
and checkpoint behavior. Segment subdivision preserves every straight corner.
Correspondence follows each shape's existing path order; there is no automatic
start-point or winding optimization. The target retains its native geometry at
completion. Arrowheads, text/glyph outlines, and general group-family matching
remain unsupported and continue to use the existing crossfade behavior.
Circular control handles follow the tangent construction in
[Manim Arc](https://docs.manim.community/en/stable/_modules/manim/mobject/geometry/arc.html).


Nested VGroup transforms recursively match children in their existing order and
morph supported outlines. Unequal child counts repeat evenly distributed source
children, fading additional copies in or out. Empty groups use zero-size,
transparent counterparts. A shape transforming to a group is wrapped in a neutral
container so its original transform is retained. Group transforms and pivots are
interpolated, and completion/restoration keeps the native target representation.
Child identities are copied at completion as before; scene-added child animation,
arbitrary Mobject families and automatic correspondence remain open.
Disconnected path alignment is described below. See **Morph nested groups** in the gallery.


Group and VGroup support child add/remove/add_to_back, indexing (including negative
indices), slicing, iteration, len, split, and a shared submobjects list. Additions
deduplicate objects and reject non-Mobjects or cycles before mutation. Re-adding a
child moves it to the end; add_to_back moves it to the beginning. Slices return a
neutral container referencing the same children, so styling a selection changes
those live objects. Slices do not inherit the original parent's transforms.
get_family lists the object and descendants in stable order, deduplicating shared
objects. Group accepts the runtime's supported geometry/text objects; other Manim
object classes and scene-family restructuring remain unimplemented. The **Build
and edit a group** example demonstrates live child editing and whole-group motion.


The `config` object supports pixel_width/pixel_height (integer 1–4096),
frame_height/frame_width (positive finite units), and six-digit hex background_color
through attributes or dict-style access. Defaults retain this preview's 800 × 450,
16 × 9 frame. Frame width follows the pixel aspect ratio; setting it adjusts frame
height. Set config before constructing the scene; Scene snapshots its own camera,
which supports the same properties and optional camera_config constructor overrides.
Camera backgrounds are captured per frame. SVG/PNG exports retain the background
and configured resolution. Config resets for every source, including after errors.
See **Configure the canvas**. Frame rate remains 15 fps; 3D, config
files, quality presets, and full ManimConfig/color semantics remain unsupported.


MovingCameraScene exposes `self.camera.frame`, an invisible rectangular Mobject.
Use `.animate.move_to(...)`, `.shift(...)`, `.scale(...)`, `.set_width(...)`, or
`.set_height(...)` to pan/zoom, and save_state/Restore to return to a prior view.
Frame samples become camera metadata, never visible geometry; scene objects keep
their own coordinates. Sequential and parallel animation timelines can include
the camera. Zoom factors/extents must stay positive and finite, with XY positions.
Setting width/height preserves aspect ratio. Rotation, 3D views, camera frame
replacement/removal effects remain unsupported. The **Pan
and zoom the view** gallery demonstrates focus changes and view restoration.


`self.camera.auto_zoom(mobjects, margin=0, only_mobjects_in_frame=False,
animate=True)` fits the combined XY bounds of one object or an iterable. Pass its
result to `self.play(...)`, or use animate=False to change the frame immediately.
The longer relative dimension determines the fit; margin adds to that full
width/height, preserving aspect ratio. `is_in_frame(object)` includes objects
partially overlapping the view. `frame_center` reads/sets the view center.
Camera frames are excluded from fitting. Empty/fully filtered selections and
nonpositive final extents raise errors without changing the camera. Bounds use
existing geometry queries: rotated groups/curves may include conservative extra
space, and text/TeX glyph dimensions are not measured. Use **Fit shapes in the
view** for animated combined framing, single-object focus, and restoration.


Mobjects support `add_updater(callback, index=None, call_updater=False)`,
remove_updater, clear_updaters, update, suspend_updating and resume_updating.
Callbacks receive the object and optionally a parameter named `dt` (seconds).
They run in scene/family order during play/wait at 15 fps. Animated object families
are suspended while their animation samples; other callbacks can query sampled
positions to follow them. Moving camera frames update even when not scene roots.
Callbacks remain Python-only and are excluded from exported frame data. See
**Follow objects each frame** for a spinner, follower and tracking camera.
This adds object callbacks, not full scene updaters,
UpdateFromFunc or custom animation subclasses. Crossfade queries use the more
visible snapshot; child queries retain this runtime's existing group coordinates.


`ValueTracker(value=0)` stores a finite real number without visible geometry.
get_value/set_value/increment_value, scalar arithmetic and in-place arithmetic are
supported. Use `tracker.animate.set_value(...)` or increment_value to drive other
objects' updaters through intermediate values. Trackers are added automatically
when animated; explicitly add a tracker whose own updater must run during waits.
For timed dependencies, add the tracker before objects that read it. Copy,
save_state/Restore, easing, parallel timelines and Succession use the existing
animation pipeline. Values occupy the tracker's x coordinate. ComplexValueTracker,
point-array access, and glyph-level numeric display semantics remain unsupported. See
**Animate a shared value** for two moving shapes and a live connector.


`always_redraw(factory)` creates an object and rebuilds its geometry/styles from
factory() each update. It follows sampled ValueTracker/animation state and supports
suspend/resume/clear_updaters. The factory must return a supported Mobject.
`mobject.become(target)` replaces geometry/styles, preserving source identity,
callbacks, suspension and checkpoint. Existing child identities are retained in
order where possible; growing/shrinking families add/drop children. Copies own
their redraw updates but factory closures still refer to the original variables.
The Python class does not change when becoming a different shape. Optional native
become fitting/stretch arguments and general scene restructuring remain unsupported.
See **Rebuild shapes each frame** for changing dimensions, suspension and freezing.


`DecimalNumber(number=0)` and `Integer(number=0)` display finite real values
using centered SVG text. get_value/set_value/increment_value and animated value
changes are supported; updaters can read a ValueTracker to display each sampled
value. DecimalNumber defaults to two decimal places; Integer defaults to zero
and rounds get_value to the nearest integer (ties to even). Formatting options
include num_decimal_places (0–12), include_sign, group_with_commas,
show_ellipsis and a plain-text unit suffix. Updates preserve position, scale,
style and callbacks. Copy, checkpoints and Restore use the existing pipeline.
Native TeX digit families, measured glyph bounds, edge_to_fix, digit indexing,
complex values and Variable remain open. See **Show changing numbers** for live
tracker labels, direct numeric animation and restoration.


`TracedPath(point_function, stroke_width=2, stroke_color=WHITE,
dissipating_time=None)` connects sampled XY positions at 15 fps. Pass a method
such as dot.get_center or a callable returning a finite point. Add the trace to
the scene; for an updater-driven source, add the source first so its callback runs
before tracing. A positive dissipating_time drops one old segment per update
after that many seconds; None or zero retains the full trail. Suspension pauses
tracing and its clock; clear_updaters freezes the trail. Copy/checkpoints and
transforms use the existing path pipeline. Trails use straight sample segments;
3D points and opacity gradients remain unsupported. **Trace moving points**
compares a full circular trail with a one-second trail that disappears during wait.


`Ellipse(width=2, height=1)` supports independent nonnegative finite dimensions,
fill/stroke styles, transforms, Create/Uncreate, growth and restoration. Its outline
can be used by MoveAlongPath or point_from_proportion; like Circle, sampling uses
angular proportion rather than constant arc-length speed. Rotated ellipse bounds
use exact analytical extents. Transforms to other supported outlines align cubic
curves; the final object retains native ellipse SVG geometry after Restore.
**Follow an ellipse** demonstrates creation, a rotated orbit, circle morphing and
restoration. Native stretch methods and general point-array editing remain open.


`Sector(radius=1)` and `AnnularSector(inner_radius=1, outer_radius=2)` create
filled circular wedges and ring sectors. Both accept start_angle, signed angle
(default PI/2, up to one full turn), arc_center and standard styles; fill_opacity
and stroke_width default to 1 and 0. Finite nonnegative radii include collapsed
geometry. Their connected outlines follow the inner arc, a radial edge, reversed
outer arc and closing edge. Create/Uncreate, MoveAlongPath, rotation, growth,
curve morphing and Restore use the existing cubic path pipeline. get_arc_center
and move_arc_center_to account for transforms. Bounds and path-speed queries use
the existing cubic approximation. **Circular and ring sectors** demonstrates
signed sweeps, outline following, unequal-curve morphing and restoration.


`Annulus(inner_radius=1, outer_radius=2)` renders a complete ring with two separate,
oppositely wound contours and no radial stroke. Fill and stroke default to 1 and
0; arc_center, standard styles and finite nonnegative radii are supported.
Create/Uncreate, growth, transforms, same-type radius interpolation and Restore
use the existing animation pipeline. Path motion traverses the outer contour
counterclockwise then the inner contour clockwise, jumping across the gap; there
is no drawn connector. Bounds use the larger radius. mark_paths_closed is accepted
as a boolean; SVG contours are always closed. Rings morph into other supported outlines with separate contour alignment;
missing contours collapse at the other outline's final endpoint.
**Rings with separate contours** shows creation, path following and changing radii.

`RoundedRectangle(corner_radius=0.5, width=4, height=2)` builds a closed cubic
outline. A finite scalar rounds every corner; a nonempty list/tuple repeats in
upper-left, lower-left, lower-right, upper-right order. Negative values produce
concave cuts. Each radius is limited to half the shorter side, following the
native corner-cut clamp. Dimensions must be finite and nonnegative; zero-sized
outlines remain stable. Create/Uncreate, path following, morphs to supported
outlines, styling, copying and Restore use the existing path pipeline. Curves
approximate circular corners with two cubic segments. General polygon
round_corners and rectangle grid lines remain open. **Rounded and concave corners**
demonstrates outline following, per-corner morphing and restoration.


`VMobject.start_new_path(point)` begins a separate contour. Continue with
add_line_to/add_points_as_corners/add_cubic_bezier_curve_to and use close_path()
to join only the current contour back to its start. has_new_path_started() reports
an unfinished anchor; get_subpaths() returns independent lists of transformed
anchors and handles (four points per cubic), excluding an unfinished anchor.
Starting another contour completes an earlier unfinished anchor as a null curve.
Reverse direction reverses contour order and winding, completing an unfinished
anchor first.

The renderer emits separate SVG moves and closes each completed loop. Path motion
weights curves by length without drawing or traversing a connector across gaps.
Transforms align contours in order, subdivide each pair independently, and add
null contours at the final endpoint when one side has fewer contours. Explicit
contour boundaries survive intermediate coincident endpoints. Annulus participates
with outer and reversed inner circles; other supported primitives use one contour.
Native representations return at completion and Restore. Automatic contour
matching, boolean geometry, smoothing and full point-array editing remain open.
**Morph separate contours** follows a square ring, morphs it to Annulus, collapses
the hole into a rounded rectangle and restores both original contours.

Supported outlines expose `get_points()`, `get_num_points()` and `has_points()`.
get_points returns independent lists of world-space anchors/handles, four points
per completed cubic plus an optional unfinished anchor. Primitive outlines use
the same cubic conversion as morphing; a single corner anchor stays one point.
Objects without supported outline geometry return no points.

`VMobject.set_points(points)` replaces raw cubic geometry; append_points extends
it, add_subpath requires complete four-point groups, and clear_points empties it.
Arrays must contain complete cubic groups, optionally followed by one new anchor,
with finite XY coordinates. Mutations validate before changing the object.
Raw edits use world coordinates and reset position/rotation/scale after baking
existing geometry, preserving styles, callbacks and checkpoints. start_new_path
also bakes existing transforms before adding its world-space anchor, so changing
the bounds does not move earlier rotated curves. append_vectorized_mobject copies
a supported outline and drops the receiver's unfinished anchor, retaining receiver
styles. These editing methods work in animate chains and with Restore. Returned
lists are copies; NumPy point-array indexing and direct mutable points attributes
remain open. **Edit cubic point arrays** builds a transformed curve from raw
points, animates its handles, appends a ring and restores the curve.

`get_subcurve(a,b)` returns an independent exact cubic portion of a supported
outline. `pointwise_become_partial(source,a,b)` replaces only the receiver's
geometry and retains its styles, callbacks and checkpoint; it also works in
animate chains. Fractions allocate equal parameter ranges to each source cubic,
as in native Manim, rather than weighting by physical distance. De Casteljau
splitting preserves the selected curve exactly, including transformed geometry.
Bounds must be finite real values and are clamped to [0,1]; reversed bounds are
rejected by pointwise_become_partial. get_subcurve permits a reversed interval
on a closed outline, wrapping through its end/start. `is_closed()` compares the
first and last anchors; `get_num_curves()` counts completed cubics. A zero-length
interval becomes a null curve. Disconnected contours stay separate. Full-range
copy includes an unfinished anchor; a partial selection with no completed source
curves leaves the receiver unchanged. **Extract and wrap curve highlights**
shows a precise cubic highlight, a wrapped circular highlight and animated
partial replacement. General glyph outlines and smoothing remain open.

`ShowPassingFlash(outline, time_width=.1)` moves an exact cubic-parameter window
along an outline, introducing the flash and removing it when playback finishes.
Use a styled copy to keep the original outline visible. Widths are finite,
nonnegative fractions; values greater than one can reveal the complete outline
at once. Groups highlight their supported children simultaneously while keeping
their original transform pivots. The removed object retains its geometry and can
be reused in `Succession`. Glyphs, arrows and per-child flash delays remain open.
Try **Traveling outline highlights** (`examples/passing_flash_scene.py`).

`NumberLine(x_range=[minimum, maximum, step])` provides linear numeric
coordinates with a shaft, ticks and optional numeric labels. A two-item range
uses step 1; ranges increase and steps are positive. `length` sets the displayed
shaft length, or `unit_size` sets scene units per number. `number_to_point`/`n2p`
convert a number (or list/tuple of numbers) to positions; `point_to_number`/`p2n`
project a point back onto the shaft. Both conversions extrapolate outside the
range and follow the number line's current shift, rotation and uniform scale.
`line @ number` and `point @ line` are equivalent shortcuts.

Options include `include_ticks`, `tick_size`, `numbers_with_elongated_ticks`,
`longer_tick_multiple`, `exclude_origin_tick`, `rotation`, and `include_tip` with
`tip_width`/`tip_height`. A range crossing zero anchors ticks at multiples of its
step; other ranges start ticks at the minimum. A tip suppresses a tick exactly at
the maximum. `get_tick_range`, `get_tick`, `get_tick_marks`, `get_start`/`get_end`,
`get_length`, `get_unit_size`, `get_unit_vector` and `get_angle` inspect geometry.
`point_from_proportion` follows the shaft. `set_length` also works in `.animate`.

Use `include_numbers=True` or `numbers_to_include` for labels, with
`numbers_to_exclude`, `font_size`, `label_direction`, `line_to_number_buff` and
`decimal_number_config` controlling numeric formatting. `add_numbers` and
`add_ticks` add independent decoration groups; `.numbers`, `.ticks` and `.tip`
access the latest matching group/tip. `get_number_mobject` makes a standalone
label. Adding decorations preserves existing world positions, including on
transformed lines. Labels use the existing centered SVG numeric text; glyph
metrics and native TeX label construction remain open. Ticks/labels are bounded
to 1000 per addition. Inverse conversion and decoration insertion require a
noncollapsed shaft. NumberLine uses the existing group renderer: animations
target the complete line, and raw partial-curve APIs do not target its shaft.
Logarithmic scaling, NumPy coordinate arrays and function plots remain open.
Try **Follow numeric coordinates** (`examples/number_line_scene.py`).

`Axes(x_range, y_range, x_length, y_length)` combines two NumberLines into a
linear XY coordinate system, centered on the middle of the coordinate rectangle.
Ranges may exclude zero. `axis_config` applies to both axes; `x_axis_config` and
`y_axis_config` override individual options, merging nested numeric formatting
options. `tips=True` is the default; origin ticks and labels are excluded by
default. The y-axis is vertical and its numeric labels sit to its left.

`coords_to_point`/`c2p` convert numeric coordinates into current world positions;
`point_to_coords`/`p2c` invert the current basis. Both follow the parent and child
axis transforms, including sampled animation frames. Conversion accepts scalar
x/y (optional zero z), a single coordinate list, batches of coordinate rows or
paired coordinate lists with scalar broadcasting. Inverse conversion accepts
one point or point rows. Batches are limited to 1000; collapsed or nearly parallel
axes cannot be inverted. `axes @ coordinates` and `point @ axes` are shortcuts.
`get_origin`, `get_x_unit_size` and `get_y_unit_size` inspect the world frame.

`add_coordinates(x_numbers, y_numbers, **number_options)` adds numeric labels,
defaulting to each axis's ticks. Both additions validate before mutation, and
existing coordinates stay fixed on transformed axes. `get_axis_labels` returns
positioned x/y labels; strings use MathTex and existing Mobjects can be supplied.
`get_x_axis_label`/`get_y_axis_label` accept a direction and buffer.
`x_axis`, `y_axis`, `axes`, `get_axes`, `get_axis`, `get_x_axis` and `get_y_axis`
expose the actual child NumberLines. Their own geometry queries use Axes-local
coordinates, as with existing group children; use c2p/p2c for world positions.
Animate the complete Axes object. General NumberPlane, function plotting,
nonlinear scaling, NumPy arrays and 3D coordinates remain open.
Try **Animate Cartesian coordinates** (`examples/axes_scene.py`), whose sampled
polyline and marker follow transformed axes through updaters.
