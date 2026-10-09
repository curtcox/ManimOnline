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
thickness do not contribute to spacing. Groups can be arranged after rotation
and nonzero scaling; direction and buffer use screen coordinates while the
group pose is preserved. Zero-scale groups cannot be arranged. Group children use local
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
measuring the visible curve's exact extrema. Arbitrary shape alignment and broader point-array semantics remain open;
disconnected contours and smoothing are described below.
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
matching, boolean geometry and full point-array editing remain open.
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
partial replacement. General glyph outlines remain open.

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
Logarithmic scaling and full NumPy coordinate arrays remain open.
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
Animate the complete Axes object. Broader graphing APIs,
nonlinear scaling, NumPy arrays and 3D coordinates remain open.
Try **Animate Cartesian coordinates** (`examples/axes_scene.py`), whose sampled
polyline and marker follow transformed axes through updaters.

`Axes.plot(function, x_range=None)` samples scalar y values into the current
world coordinate frame. Its default step is the axis tick step divided by
`num_sampled_graph_points_per_tick` (default 10). A two-item range keeps this
sampling density; a three-item range supplies an explicit step. Plots are
independent geometry after construction; use `always_redraw` to follow changed
parameters or axes. `input_to_graph_point(x, graph)`/`i2gp` evaluate the original
scalar function at x in the current axes, independently of later graph transforms.
`plot_parametric_curve(function, t_range=...)` maps XY coordinate functions into
the axes. Both plotting methods return `ParametricFunction` vector paths.

`ParametricFunction(function, t_range=(0,1))` samples finite XY scene points;
two-item ranges use step .01. `FunctionGraph(function, x_range=...)` samples
scalar y values in scene coordinates, defaults to the frame width and uses
yellow. `get_function` returns the supplied function, and
`get_point_from_function(t)` queries its original scene coordinates.
`generate_points` replaces geometry with fresh function samples. Callbacks stay
out of frame JSON. Sampling includes the exact final parameter and is bounded
to 10001 points per object.

Smoothing is enabled by default: open paths have natural endpoint conditions,
and closed paths use periodic cubic joins. `use_smoothing=False` uses straight
segments. `discontinuities=[...]` with `dt` excludes buffered parameter intervals
and creates separate contours; overlapping gaps merge. Declare discontinuities
explicitly—sampling does not detect singularities or adapt to curvature.
Nonfinite values and nonzero z coordinates fail clearly. Vectorized callbacks,
nonlinear scaling, color scales, implicit plots and broader graph analysis remain
open. Existing preview size/deadline limits still apply to dense animations.

VMobjects also provide `set_points_smoothly`, `make_smooth`, `make_jagged` and
`change_anchor_mode('smooth'/'jagged')`, including `.animate`. These preserve
contour boundaries, styles and checkpoints. Handle changes compensate for
changed bounds so transformed anchors remain fixed during animated smoothing.
Pending anchors are retained; smoothing targets this object's own geometry.
Try **Plot smooth functions** (`examples/plot_scene.py`) for a changing parabola,
tracked input, passing highlight and closed parametric loop.


`NumberPlane` extends Axes with Cartesian background lines. Unspecified ranges
span the configured frame; unspecified lengths give one scene unit per numeric
unit. Axes omit ticks and tips by default, with 24-point numeric labels.
`background_line_style` sets the major lines (default `BLUE_D`, width 2);
`faded_line_style` configures subdivisions, defaulting to half the major width
and opacity. `faded_line_ratio=2` divides each major interval into two; 0 or 1
omits subdivisions. Line positions follow Manim's origin-relative, open-boundary
grid convention, including ranges that exclude zero. The grid is limited to
1000 lines and the ratio must be a nonnegative integer.

`background_lines`, `faded_lines`, `x_lines` and `y_lines` expose local children;
x_lines are horizontal major lines, y_lines vertical. Labels, plotting and
coordinate conversions work through inherited Axes methods. `get_vector(coords,
**style)` makes an independent Arrow from the current numeric origin to coords.
Use `always_redraw` to follow a moving plane. The accepted
`make_smooth_after_applying_functions` flag stores metadata; nonlinear
transform preparation and function application are still open.
Try **Move a Cartesian grid** (`examples/plane_scene.py`) for animated coordinates,
a function plot, rotation, scaling, restoration and vector cleanup.


`ComplexPlane` extends NumberPlane with complex-valued coordinate conversion.
`number_to_point`/`n2p` map finite complex-compatible scalars (including real
numbers) through the current XY frame; `point_to_number`/`p2n` return a Python
complex number by inverting that frame. Rotation, scaling, translation and
sampled animation frames use the same conversion as Cartesian axes.

`get_coordinate_labels(*numbers, **number_options)` returns independent,
world-positioned DecimalNumber labels without attaching them. `add_coordinates`
attaches labels while keeping existing coordinates fixed. With no arguments,
labels follow each axis's tick range. Explicit values use the dominant component:
imaginary magnitude greater than real selects the imaginary axis and appends
`i`; ties select the real axis. Each label gets independent formatting options.
`coordinate_labels` returns the latest queried or attached group. Attached
children use the plane's local coordinates. Copies and saved-state restoration
retain labels; numeric text uses the existing SVG font renderer.
Try **Animate complex coordinates** (`examples/complex_scene.py`) for a complex
value and its conjugate following a rotating plane. Complex function application,
nonlinear warping, complex ValueTracker values and native TeX digit families
remain open.


Graph calculus uses scalar function providers. `input_to_graph_coords`/`i2gc`
return `(x, f(x))` in numeric coordinates. `angle_of_tangent(x, graph, dx=1e-8)`
and `slope_of_tangent` use a forward finite difference, with angles and slopes
measured in numeric coordinates, independent of the axes' world rotation or
unequal scale. dx must be finite and nonzero and must change the floating-point
input; negative dx reverses the returned angle's direction.

`plot_derivative_graph(graph, color=GREEN, **plot_options)` samples numerical
slopes into a new plot. `plot_antiderivative_graph(graph, y_intercept=0, samples=50,
**plot_options)` integrates the original scalar provider from zero to each input
using evenly spaced trapezoids. Negative inputs use signed intervals; samples
must be an integer between 2 and 10000. Both default to the axes' plotting range
and accept ordinary plotting options, including declared gaps. Vectorized function
execution remains unsupported. Integration evaluates the entire interval from
zero, so declared plotting gaps do not avoid singularities inside that interval.
These numerical helpers do not perform symbolic differentiation or adaptive
integration; results depend on step size, resolution and floating-point precision.

Try **Follow a tangent and derivative** (`examples/calculus_scene.py`) for a sine
curve, its numerical derivative, an integrated approximation and a moving tangent
with a slope readout. Labeled secants and continuous graph regions are described below.


`get_riemann_rectangles(graph, x_range=None, dx=.1)` builds a VGroup of Rectangle
objects with polygon geometry. Cells follow the axes' XY basis, including world
rotation or unequal scale. Samples may be `left`, `right` or `center`; rectangles
start at each partition input and the last interval may extend beyond the upper
bound. A third x_range item is ignored in favor of dx. `width_scale_factor=1.001`
overlaps adjacent cells slightly; the chosen sample stays within each cell.

Without a range, cells use the graph's parameter bounds, or their intersection
with `bounded_graph`. A bounding function's baseline is evaluated at the left
partition input; otherwise the baseline is zero clamped into the y range.
`show_signed_area=True` inverts fill colors below the baseline. `color` accepts a
single six-digit hex color or up to 64 gradient stops. `fill_opacity`,
`stroke_color`, `stroke_width` and `blend=True` control cell styling. dx and width
scale must be positive and finite; groups are limited to 1000 cells before
providers are called. These are independent snapshots; regenerate them to follow
changing functions or axes. Declared plot gaps do not suppress cell sampling.
Try **Refine signed area estimates** (`examples/riemann_scene.py`) for refinement
and the region between two functions. Color types beyond hex strings remain open.


`Axes.get_secant_slope_group(x, graph, dx=None)` draws horizontal dx and vertical
function changes, plus an optional extended secant line. None or zero dx uses a
tenth of the axis range; negative intervals reverse label sides. Set
`include_secant_line=False` to omit the extended line, or change its length and
colors. String/numeric labels use MathTex; supplied Mobjects are copied. Access
components through dx_line, df_line (also dy_line), dx_label, df_label (also
dy_label), and secant_line when present. Lines use world horizontal/vertical
changes even on rotated axes, following the Community convention. Labels shrink
to fit both changes; font sizes use estimates rather than measured glyph bounds,
and a zero change collapses labels. Regenerate groups with always_redraw to
follow changed inputs. Try **Follow a labeled secant** (`examples/secant_scene.py`).


`Axes.get_area(graph, x_range=None, color=(BLUE, GREEN), opacity=.3)` returns a
Polygon filling the region between a plotted curve and numeric y=0. Pass a second
curve as `bounded_graph` to fill between curves. The default range is the primary
plot's range; a bounding curve clips that interval to its own range and rejects
nonoverlapping ranges. Explicit ranges need exactly two finite nondecreasing values.
Endpoint functions are evaluated exactly, while interior vertices come from the
existing plotted anchors and control points, following Community's polygon
construction. Independent graph transforms affect those interior points; redraw
the plots and regions together when changing axes. Declared plot gaps are joined
by the polygon, so this helper does not split singular/disconnected regions.

Use a hex color or up to 64 hex gradient stops. Gradients run left to right in
the polygon's local bounding box, with self-contained SVG paint definitions that
survive SVG/PNG export. Opacity controls fill and border; pass `stroke_width=0`
for a borderless region. Regions are independent snapshots and can use
always_redraw for changing bounds. Try **Fill changing graph regions**
(`examples/area_scene.py`) for expanding bounds, gradients, a region between
functions, transformation and cleanup. Adaptive integration and more general
region topology remain open.


`DashedLine(start=LEFT, end=RIGHT, dash_length=.05, dashed_ratio=.5)` creates
individually addressable Line segments in a VGroup-compatible Line. The dash count
is at least two, based on span, requested dash length and occupied ratio, and is
limited to 1000. Open patterns start and end with a dash; ratios from zero to one
are supported. Transformations and endpoint queries follow the actual child
geometry. `get_first_handle` and `get_last_handle` query the end segments.
Endpoint changes stretch the existing family, preserving segment edits and colors;
regenerate the object to recompute dash count. Copies, restore, group animations,
and per-segment styling use the existing family pipeline. Curved DashedVMobject construction is described below.

`Line.get_projection(point)` and `NumberLine.get_projection(point)` project onto
the infinite current world-space shaft, including beyond its endpoints. A collapsed
shaft returns its start. Axes offers `get_vertical_line(point)` from the x-axis,
`get_horizontal_line(point)` from the y-axis, and `get_lines_to_point(point)` in
horizontal/vertical order. The default is DashedLine; pass `line_func=Line` for a
solid guide. `get_line_from_axis_to_point(index, point)` accepts axis 0 or 1.
Guides use perpendicular projection onto the current axes, including independently
rotated shafts, rather than assuming screen vertical/horizontal directions.

Use `line_config` for dash/style options; it is copied before construction.
The helper's `color` and `stroke_width` override those entries, defaulting to white
and 2. Guides are world-positioned independent snapshots. Use always_redraw with
current graph/tracker inputs to follow movement; reading another object's updater
can see its previous position when that updater runs later. Try **Follow dashed
coordinate guides** (`examples/guides_scene.py`) for a moving point, a rotating
coordinate frame and cleanup.


`DashedVMobject(outline, num_dashes=15, dashed_ratio=.5, dash_offset=0,
equal_lengths=True)` creates independent cubic subcurves in a VMobject with
VGroup behavior. It supports the current line, polygon, circle, ellipse, arc,
ring and VMobject paths. Source styling and world geometry are copied; use
`set_color` on the source or result to choose dash colors. The source is unchanged.
Counts are integers from 0 to 1000; zero returns an empty group. Ratios range from
zero to one. Negative/positive phase offsets wrap modulo one pattern period.

Open patterns start and end with a dash at zero phase; shifted end pieces are
clipped or reappear at the beginning. A shifted open pattern can have one extra
piece. Closed patterns wrap exactly through the seam, including full coverage
with one dash. Equal-length spacing uses a 20-segment-per-cubic distance lookup;
`equal_lengths=False` divides the curve parameter instead. Cuts use exact cubic
subdivision, but length spacing is approximate. Disconnected contours keep their
separate paths and do not add gap distance to the length calculation.

`Mobject.get_arc_length(sample_points_per_curve=10)` measures its own path using
straight sampling pieces. The sample count is an integer from 2 to 1000, with a
200000-segment lookup cap. Containers without their own points return zero.
Dashes are independent snapshots; regenerate them to follow changing geometry or
phase. Copies, restore, group morphs and creation/removal use the existing family
pipeline. Arrow tips, glyph paths and general geometry-bearing families remain
open. Try **Dash curved paths and shift their phase**
(`examples/dashed_paths_scene.py`) for a wrapped ring, both spacing modes and
animated refinement.


`TangentLine(path, alpha, length=1, d_alpha=1e-6)` constructs a world-space
finite-difference tangent on the supported XY outlines. alpha is a finite
proportion in [0,1]; sampling uses the existing path-query behavior at
`alpha-d_alpha` and `alpha+d_alpha`, clipped to the endpoints. The tangent is
centered on the sample chord's midpoint, with the requested nonnegative length.
At path ends it uses a one-sided chord. Its direction reflects the current source
geometry and transforms. Source geometry is unchanged and no source reference is
stored; use always_redraw to follow motion or a changing requested length.

The sampling distance must be positive and finite. Coincident samples, an
unrepresentable change in proportion, collapsed paths and sampling an entire
closed path are rejected. Corners and contour jumps give a finite chord rather
than a unique smooth tangent. Accuracy depends on the sampling distance and the
existing path sampler. Tiny resolved spans normalize without reciprocal overflow.
Try **Follow tangents along curved paths** (`examples/tangent_paths_scene.py`)
for an ellipse and cubic curve with moving markers and growing tangents.

Line, DashedLine and NumberLine expose `get_slope()` and `set_angle(angle,
about_point=None)`. The slope is tan of the current world angle, with ordinary
floating-point behavior near vertical. Angle changes rotate around the start by
default and support animate. `Line.set_length(length)` and inherited DashedLine/
TangentLine behavior scale around the current center, accepting a finite
nonnegative length. Positive resizing of a collapsed line needs fresh endpoints
first. Dashed resizing preserves its existing count and child edits. NumberLine
keeps its existing positive-length resize validation.


### Angle markers

Try **Mark angles between moving lines** (`examples/angle_scene.py`) for a
rotating ray, a changing degree label, a dotted circular mark and a right-angle
corner. `Angle` supports quadrant signs, signed clockwise/counterclockwise sweeps,
automatic or explicit radius, dots and `from_three_points`. `RightAngle` builds
an elbow mark; `Elbow` also works as an independent path. Parallel or zero-length
lines produce an empty angle. Use `always_redraw` to follow moving lines.
Angle now stores its own arc/corner path and only the optional dot as a child.
Its path supports point queries, edits, reversal and partial extraction. `get_value` is the
construction-time angle, and `get_lines` returns the defining lines. Full Manim
Community compatibility remains unfinished.


### Endpoint arcs

Try **Bend arcs between moving endpoints** (`examples/endpoint_arc_scene.py`).
`ArcBetweenPoints(start, end, angle=PI/2, radius=None)` creates a circular XY
path between coordinates. Signed angles select direction, including sweeps larger
than a semicircle. A signed radius overrides the angle and selects the shorter
arc; its magnitude must be at least half the endpoint distance. Angle zero makes
a straight path and coincident endpoints collapse to a point. Use `always_redraw`
for changing endpoints or bend. Full turns and unresolvable extreme floating-point
geometry are rejected; arbitrary 3D arcs and general Arc/Circle tip attachment remain open.


### Polygons with curved edges

Try **Morph polygons with curved edges** (`examples/arc_polygon_scene.py`).
`ArcPolygon(*vertices, angle=PI/4, radius=None, arc_config=None)` closes a path
with endpoint arcs; `arc_config` accepts one shared dictionary or one dictionary
per edge. `ArcPolygonFromArcs(*arcs)` copies a closed outline from existing arcs,
joining gaps and the last endpoint with straight segments. Both retain defining
arcs as children, available through `.arcs`, with independent colors and strokes.
The renderer now paints geometry-bearing families' own paths and child geometry,
including global depth ordering and creation. Parent transforms use the existing
local-child coordinate convention. Outline and child morphs are aligned
independently; automatic matching of unrelated edges remains unfinished.


Try **Follow and restore an editable angle path**
(`examples/angle_path_scene.py`) for movement along the angle, morphing into a
corner, and restoration of the original path and dot. Mutable NumPy point-array attributes and glyph-level family geometry remain unfinished.


### Children on ordinary shapes

Try **Attach and restore children on shapes** (`examples/shape_family_scene.py`).
Mobject and ordinary shapes now support `add`, `add_to_back`, `remove` and
`submobjects` assignment, with duplicate removal and cycle checks. A shape's
`split`, iteration, indexing and slices include the shape itself before its
children when it has an extractable path. `family_members_with_points` filters
recursive families by actual supported geometry. Shapes still render their own
outline while hosting children; empty base Mobject containers render descendants.
Children use local-to-parent coordinates. Bounds now combine own outlines and externally placed children. Glyph-level
families and general scene restructuring remain unfinished.


### Bounds and camera framing for families

Try **Frame shapes and distant children** (`examples/family_bounds_scene.py`).
Size and edge queries now include both the parent's outline and nested children.
`get_width`, `get_height`, `get_left/right/top/bottom`, `get_corner` and
`get_edge_center` expose the XY boundary used by positioning and camera fitting.
Adding/removing/replacing children on an already transformed ordinary shape
preserves its existing geometry's world position. Bounds are conservative for
rotated families and cubic controls; browser text metrics remain incomplete.
Direct child motion on ordinary shapes also preserves the parent and siblings.
Try **Move children inside transformed shapes** (`examples/child_motion_scene.py`)
for a tracked dot inside a rotated/scaled rectangle. Group/VGroup now share this compensation. Native world-space child coordinates
remain incomplete.

Try **Move children inside nested groups** (`examples/group_motion_scene.py`).
Moving and adding/removing distant children preserves stationary siblings in
rotated/scaled nested Group and VGroup families, including coordinate helpers.


### Layout after rotation and scaling

Try **Arrange rotated and scaled groups** (`examples/transformed_layout_scene.py`).
Group/VGroup `arrange` now supports rotated, positively or negatively scaled
families, screen-space gaps and aligned edges, centering, and `.animate` chains.
Stationary first children stay fixed with `center=False`; child references and
shape orientations survive rearrangement and restoration. Collapsed zero-scale
groups remain unsupported. Bounds retain the conservative curve/text limits
described above.


### Animated grid layout

Try **Reflow a transformed grid** (`examples/grid_layout_scene.py`).
`Group.arrange_in_grid` and `VGroup.arrange_in_grid` support explicit or inferred
rows/columns, scalar gaps or `(horizontal, vertical)` gaps, `cell_alignment`,
`row_alignments` (`u/c/d`), `col_alignments` (`l/c/r`), optional `row_heights` and
`col_widths` with `None` for automatic measurement, and all eight `flow_order`
values (`rd`, `dr`, `ld`, `dl`, `ru`, `ur`, `lu`, `ul`). Layout preserves the
starting group center, shape orientations, and live child references, including
`.animate` and checkpoint restoration. Incomplete final rows/columns are allowed.

Grid cells use screen-space bounds and have a 1000-cell limit. Zero-scale groups
cannot be arranged; text/curve bounds retain the limits above. Layout now also applies to children on ordinary geometry-bearing parents.


### Layout of children on shapes

Try **Arrange children on a shape** (`examples/shape_layout_scene.py`).
Mobject and ordinary shapes now inherit `arrange`, its `arrange_submobjects`
alias, and `arrange_in_grid`. These methods lay out direct children, excluding
the parent's own outline. Row arrangement with `center=False` keeps the first
child and own outline fixed; centering moves the whole family. Grid arrangement
preserves the family center. Supported rotation/nonzero signed scale, animation,
child references, and checkpoint restoration use the same behavior as groups.
Zero-scale families, glyph bounds, and native world-space child coordinates
remain unfinished.


### Editable arrow-tip geometry

Try **Edit arrow tip outlines** (`examples/tip_geometry_scene.py`).
`ArrowTriangleTip`, `ArrowTriangleFilledTip`, and `StealthTip` now provide closed
editable VMobject outlines, styles, path queries, layout, transforms, morphing,
copying, and restoration. The abstract `ArrowTip` base supplies `tip_point`,
`base`, `vector`, `tip_angle`, and `length` properties. Dimensions are nonnegative
and finite; triangle `width` and `start_angle` control its outline. Triangle
bounds are centered locally. Stealth tips use the concave outline and an
enclosing-triangle length; their start_angle is metadata, as in the referenced
constructor.

Try **Manage arrow tips and shafts** (`examples/arrow_tips_scene.py`). Arrow now
attaches real editable tip children. Line/Arrow support `add_tip`, `pop_tips`,
`has_tip`, `has_start_tip`, `get_tip`, `get_tips`, `tip`, and `start_tip`.
Shaft endpoints track tip bases, including during endpoint animations and
restoration. Arrow defaults to a .25 endpoint buffer, a filled triangular tip,
and length-based caps for tip size and stroke width. `buff=0` touches the given
endpoints; coordinate-plane vectors retain this behavior automatically.
Arrow.scale keeps world tip size by default; `scale_tips=True` scales the whole
family. Tip coordinates follow the runtime's parent-local child convention.
Full native tip-family behavior and straight Arrow partial-path/morph support
remain unfinished.


Try **Render circular and square arrow tips** (`examples/round_square_tips_scene.py`).
`ArrowCircleTip`, `ArrowCircleFilledTip`, `ArrowSquareTip`, and
`ArrowSquareFilledTip` supply editable closed paths and attach to either end of
Line/Arrow. Outline tips default to no fill and a 3-unit stroke; filled tips have
full fill and no stroke. `length` sets the circle diameter or square side.
Circle `start_angle` selects its first anchor; square `start_angle` is metadata,
as in the native constructor. Square tip length queries measure the corner-to-
opposite-corner diagonal. These classes support the existing path editing,
transforms, partial curves, tip queries, copying and restoration.


Try **Animate two-ended arrows** (`examples/double_arrow_scene.py`). `DoubleArrow`
extends Arrow and adds a real filled triangular start tip by default. Configure
each end independently with `tip_shape_start` and `tip_shape_end`; the latter
replaces `tip_shape` for the end tip when both are supplied. It inherits Arrow's
endpoint buffer, sizing caps, fixed-size tip scaling, endpoint editing, tip
management, copying and checkpoint animation. Tip coordinates retain the
runtime's parent-local convention; see curved-arrow support below.


Try **Animate tangent-aligned curved arrows** (`examples/curved_arrow_scene.py`).
`CurvedArrow(start_point, end_point, **style)` and `CurvedDoubleArrow` extend the
XY endpoint-arc implementation with real tangent-aligned tips. Configure `angle`
or signed `radius`, `tip_length`, and `tip_shape`; curved double arrows also accept
`tip_shape_start`/`tip_shape_end`. They support tip management, endpoint queries,
arc-center positioning, ordinary family scaling/rotation, direct or animated
`put_start_and_end_on`, copying and restoration. Scaling includes tip geometry.
The shaft fits to actual tip bases on each sampled frame. Endpoint fitting
preserves curve shape with a uniform rotation/scale; it cannot expand collapsed
curves. General Arc/Circle tip attachment, native world-coordinate children,
3D paths and full tip-bearing partial-path behavior remain unfinished.


Try **Style and build arrow tips** (`examples/tip_style_scene.py`). Line and the
straight/curved arrow classes accept `tip_style` dictionaries. Tip fill/stroke
colors, opacities and stroke widths can differ from the shaft. `get_unpositioned_tip`
creates a standalone tip; `create_tip` positions a detached tip, and `position_tip`
positions a supplied tip. Attach with `add_tip` after configuring it.

`add_tip`, `create_tip`, and `get_unpositioned_tip` accept `tip_width`. Following
Manim's factory rule, this controls the built-in filled triangular shape; its
default width follows the connector's default tip length. Other tip shapes retain
their own constructor dimensions. `tip_style` overrides generated defaults,
including a triangular `width`. Factory dimensions are finite and nonnegative;
unsupported style options fail explicitly. Positioned tip coordinates use the
runtime's parent-local convention. `get_tip()` returns the end tip or, if only a
start tip exists, that start tip.


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


Try **Stretch nested vector shapes** (`examples/stretch_scene.py`). `stretch(factor,
dim, about_point=..., about_edge=...)` now deforms editable XY geometry along the
chosen screen axis, including rotated/scaled nested families, own outlines and
real arrow-tip children. Negative factors reflect geometry; zero collapses the
chosen axis. Original objects, ordered child identities, styles and updaters are
retained. The operation validates a copied family before replacing live state.

`stretch_to_fit_width`/`stretch_to_fit_height`, `rescale_to_fit(..., stretch=True)`,
`replace(..., stretch=True)` and `Circle.surround(..., stretch=True)` use this path.
Stretching a circle can produce an oval; stretched surrounding follows the target's
aspect ratio, then fits its width to the target diagonal times buffer_factor,
matching the implementation of Manim's Circle helper. Own analytical shapes
materialize into editable cubics. Bounds therefore use conservative cubic control
boxes. Straight connectors retain endpoint APIs; curved shafts bake their displayed
geometry before tip deformation, so similarity fitting cannot undo the stretch.
Subsequent tip replacement/removal still lacks full native path-reset semantics.

Stretch-aware transforms use materialized geometry at both ends so animated
stretching interpolates world coordinates and restoration retains the saved
shape type. XY coordinate axes continue to map/invert points after stretching.
Text/MathTex glyph stretching, camera-frame stretching, shared descendants under
multiple parents and 3D remain explicit gaps; unsupported families fail without
changing live objects. Zero-size fitting dimensions retain the existing no-op.


Try **Shear and warp vector shapes** (`examples/point_map_scene.py`). `apply_matrix`
now applies finite matrix blocks of one to three rows/columns, embedded in a 3D
identity matrix as in Manim. The result must preserve the XY plane. A 3 × 3 input
is a spatial matrix, not a homogeneous translation matrix. `apply_function`
maps each XY anchor/control point, while `apply_complex_function` maps x + iy and
returns its real/imaginary coordinates. These APIs default to the screen origin;
explicit about_point/about_edge select another pivot. Stretch retains its center
default and shares the same family traversal.

Mappings compose existing parent transforms, preserve object/child identities,
styles, pending anchors and disconnected contours, and validate a copied family
before replacing live state. Nonlinear maps convert polygon edges and straight
connectors to cubic paths so their control points can bend. Matrix maps keep
straight endpoints. Animated maps interpolate mapped world geometry, and Restore
returns the saved types. Nonlinear mapping transforms control points; it is not
adaptive resampling of the entire continuous curve. User callbacks receive actual
path coordinates, not synthetic container origins.

Glyph/camera/shared-family mapping, arbitrary 3D, native NumPy arrays, adaptive
nonlinear preparation, post-warp connector/tip mutations and analytical arc-center
queries after nonlinear deformation remain unfinished. Coordinate helper inversion
does not become a general nonlinear inverse merely because its outline is warped.


Try **Align to edges and color gradients** (`examples/positioning_scene.py`).
Everyday positioning helpers now follow Manim Community: `to_edge`, `to_corner`,
`align_on_border`, `center`, `align_to`, `get_x/get_y/get_coord`,
`set_x/set_y/set_coord`, `match_x/match_y`, `match_width/match_height` and
`move_to(..., aligned_edge=..., coor_mask=...)`. Edge placement uses the current
preview `config` frame. `scale` and `rotate` accept `about_edge`; `rotate` accepts
an `axis` (OUT/IN, or a half turn about an in-plane axis, which is an XY reflection),
and `flip()` mirrors about the object's center. `Rotate` accepts `about_edge`.

The full Community color palette (`BLUE_A`…`BLUE_E`, `TEAL`, `GOLD`, `MAROON`,
`GRAY_A`…`GRAY_E`, `PURE_RED`, `LOGO_*` and GRAY/GREY aliases) and buffer constants
(`SMALL_BUFF`, `MED_SMALL_BUFF`, `MED_LARGE_BUFF`, `LARGE_BUFF`) are available.
`YELLOW`, `ORANGE` and `PINK` now use Community's values. Color helpers
`interpolate_color`, `color_gradient`, `average_color`, `invert_color`,
`color_to_rgb` and `rgb_to_color` work on six-digit hex strings; `ManimColor`
objects and named-color strings are not implemented. Mobjects gain style getters,
`match_color`, `match_style`, `set_color_by_gradient`,
`set_colors_by_radial_gradient`, `fade`, `fade_to`, `sort` and `invert`; these
work in `.animate` chains. Z coordinates other than zero, general 3D rotation axes
and text flipping (glyph mapping) remain unsupported and fail explicitly.


Try **Polygrams, stars and shape matchers** (`examples/polygram_scene.py`).
`Polygram`, `RegularPolygram`, `RegularPolygon`, `Star` and `round_corners` follow
Community's vertex order, start angles, density handling and default inner star
radius. `Polygon`, `Triangle`, `Rectangle` and `Square` are now `Polygram`
subclasses with Community defaults: polygons are BLUE, rectangles WHITE, vector
strokes 4 wide, and `Triangle` is a unit-radius `RegularPolygon` (larger than the
previous preview triangle). `get_vertices`/`get_vertex_groups` return world points.

`SurroundingRectangle` (PURE_YELLOW, `buff` number or x/y pair, optional
`corner_radius`), `BackgroundRectangle`, `Cross`, `Underline` and
`add_background_rectangle` are available. Shifting and scaling a `Group`/`VGroup`
now moves its children in world space, as in Manim, so `group[0].get_center()`,
matchers and arrows between members of a moved group land where expected.
Rotation is still stored on the group: children of rotated groups keep
parent-local coordinates. Text has no measured bounds yet, so matchers around text
are not sized to the glyphs.


Try **Measured text and formula layout** (`examples/text_layout_scene.py`).
`Text`, `DecimalNumber`/`Integer` and `MathTex` now have ink bounds, so `next_to`,
`to_edge`, `arrange`, `SurroundingRectangle`, `Underline` and camera framing use
their real size. Sizes follow Manim Community: a `Text` em is `font_size/72` scene
units, a TeX em (`MathTex`, numbers) is `font_size/96`, and multi-line `Text`
lines are `1.3 · font_size/96` apart (`line_spacing` adjusts this). Text and
formulas therefore render about half as large as in earlier previews, matching
Manim. `Text` is drawn in Liberation Sans/Arial with each line's width pinned to
the Python layout; `font`, `slant` and `weight` are passed to the browser.
Numbers use Community's TeX digit layout in a serif face. Formulas are typeset
and measured by MathJax: the first render estimates unmeasured formulas, then the
page re-renders once with the measured sizes (cached for later renders).
Per-character text APIs (`t2c`, indexing glyphs), MarkupText, Paragraph and exact
system-font metrics are not implemented.


Try **Entrances, emphasis, swaps and exits** (`examples/animation_tour_scene.py`).
All Community rate functions are available (`rate_functions.ease_out_bounce`,
`there_and_back_with_pause`, `running_start`, `squish_rate_func`, …; `smooth` is
now Community's sigmoid curve rather than smoothstep). Animations accept
`lag_ratio`, `remover` and `reverse_rate_function`; `Create` draws group members
in sequence by default (`lag_ratio=1`), and `Write`/`Unwrite`/`DrawBorderThenFill`
follow Community's outline-then-fill phases and length-based defaults (text shows
a stroked outline, then its fill). `FadeIn`/`FadeOut` accept several mobjects,
`shift`, `target_position` and `scale`. New animations: `GrowArrow`,
`GrowFromEdge`, `SpinInFromNothing`, `Circumscribe`, `Flash`, `Wiggle`,
`FocusOn`, `FadeTransform`, `ClockwiseTransform`, `CounterclockwiseTransform`,
`Swap`/`CyclicReplace`, `MoveToTarget` with `generate_target()`, `ApplyMethod`,
`ScaleInPlace`, `FadeToColor`, `UpdateFromFunc`, `UpdateFromAlphaFunc`,
`ShowIncreasingSubsets`, `ShowSubmobjectsOneByOne`, `AddTextLetterByLetter`,
`RemoveTextLetterByLetter` and `Wait`. `Transform` accepts `path_arc`.

Scene membership now follows Community: re-adding a mobject brings it to the
front, adding a group absorbs members that were added on their own, removing a
member splits its group, and members of on-screen groups can be animated in
place (e.g. `Indicate(equation[0])`). Members of rotated or transformed groups
must still be animated through the whole group. `play(rate_func=...)` overrides
each animation's rate function, and a transform whose rate function ends at 0
(such as `there_and_back`) finishes at its starting state. Glyph-level
`TransformMatchingShapes`/`TransformMatchingTex`, `ApplyWave` and `Homotopy`
are not implemented.


**NumPy.** `from manim import *` provides `np` when NumPy is available. The worker
loads Pyodide's NumPy package (about 12 MB, cached for offline use after the first
download) only when a script mentions `np` or `numpy`. Preview APIs accept NumPy
arrays and scalars (including `np.int64`) and return plain tuples/floats; frames
are converted to plain JSON numbers. Mobject points are not stored as NumPy arrays,
so code that mutates `mobject.points` in place is not supported.


Try **Titles, braces, bullets and variables** (`examples/annotation_scene.py`).
`Brace` uses Community's SVG brace outline and construction (sharpness, buff,
any XY direction, tip/direction queries, `put_at_tip`, `get_tex`, `get_text`);
`BraceLabel`, `BraceText` and `BraceBetweenPoints` are available. `Tex` typesets
LaTeX text mode with `$math$` through MathJax `\text{}` runs (plus `\textbf`,
`\textit`, `\emph`, `\texttt`, `\textrm`, `\textsf`; other text macros fail
explicitly). `Title`, `BulletedList`, `Vector`, `LabeledDot`, `Variable`, `always`,
`f_always`, `always_shift` and `always_rotate` follow Community. `.animate` now
accepts any mobject method (not updater/checkpoint bookkeeping).

The default frame is now Community's 14.22 × 8 units (it was 16 × 9), so
`to_edge`, `Title` and other frame-relative placement match Manim, and strokes
are drawn like Manim: `stroke_width × 0.01` frame units, unchanged by object
scale and constant on screen while a moving camera zooms. Strokes therefore look
thinner than before and scale with the player size. Bounds follow Community's
rules: edges, centers and `next_to` use path anchors, while `width`/`height`
include Bézier handles; rotated straight-edged shapes report the bounds of their
rotated points.


Try **Formula parts and matching transforms** (`examples/formula_parts_scene.py`).
`MathTex` with several strings, `substrings_to_isolate` or `tex_to_color_map`
now has Community-style parts: `eq[i]`, `get_part_by_tex`, `get_parts_by_tex`,
`index_of_part_by_tex`, `set_color_by_tex`, `set_color_by_tex_to_color_map` and
`set_opacity_by_tex`, and parts can be animated individually (`Indicate(eq[2])`).
`TransformMatchingTex` slides parts with equal tex strings into place and fades
the rest (with `key_map`, `transform_mismatches`); `TransformMatchingShapes`
matches drawable members by normalized outline. Parts are typeset together with
MathJax `\class`, so TeX spacing is unchanged; each part's position comes from
the browser's measurement on the second render pass. Glyph-level indexing inside
a part (`eq[0][1]`) is not implemented.


Functional animations now follow Community: `ApplyPointwiseFunction`,
`ApplyPointwiseFunctionToCenter`, `ApplyMatrix`, `ApplyComplexFunction` (with its
arc path), `ApplyFunction`, `Homotopy`, `SmoothedVectorizedHomotopy`,
`ComplexHomotopy`, `ApplyWave`, `PhaseFlow`, `ChangingDecimal` and
`ChangeDecimalToValue`. `Label`, `LabeledLine`, `LabeledArrow` and
`AnnotationDot` are available. Nonlinear maps bend cubic control points, so a
waved or flowed outline becomes an editable cubic path.


Try **Matrices, determinants and tables** (`examples/matrix_table_scene.py`).
`Matrix`, `DecimalMatrix`, `IntegerMatrix`, `MobjectMatrix`, `get_det_text`,
`matrix_to_tex_string` and `matrix_to_mobject` follow Community, including
stretched TeX brackets, row/column access and coloring. `Table`, `MathTable`,
`MobjectTable`, `IntegerTable` and `DecimalTable` support labels, inner/outer
lines, cells, highlighted cells, `create()` and scaling; `Paragraph` lays out
lines on Community's baseline pitch with left/center/right alignment. Text and
formulas can now be stretched along their own axes (`stretch_to_fit_height`),
which brackets and parentheses rely on; stretching rotated glyphs (a shear) is
still unsupported.
