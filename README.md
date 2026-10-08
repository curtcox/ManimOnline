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
renders immediately and cancels scheduled work for earlier edits.

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

- Shapes: `Circle`, `Arc`, `Dot`, `Square`, `Rectangle`, `Line`, `Arrow`, `Triangle`, `Polygon`,
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
  rectangles, and triangles, including their 2D geometry transforms.
- Timing: `run_time`, `linear`/`smooth` rate functions, simultaneous animations,
  and nested animation groups with staggered starts.
- Directions support vector addition/subtraction and scalar multiplication,
  such as `RIGHT * 2`.

`Create` progressively traces primitive shape outlines and fades in their fill;
`Uncreate` reverses that draw and removes the object. Groups reveal all children
simultaneously. Text creation and `Write` use fades because glyph paths are not
available in this runtime. MathTex creation also uses fades. Arrow shafts and heads reveal together. Transforms
interpolate matching geometry and crossfade between different shape types.
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
smooth easing; use `rate_func=linear` for constant speed. Paths are snapshotted
at animation start. Circles use exact circular sampling from the positive X
axis counterclockwise; polygon outlines follow their vertex order and close
back to the first vertex. Square/rectangle paths start at the upper right
corner; triangles start at their top vertex. Straight edges are sampled by
distance, so longer edges take proportionally longer. Path sampling is limited
to the XY plane; groups, text, arrowheads, arbitrary curves, and live path
updates are unsupported. This is preview geometry, not Manim's Bézier engine.

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
for loading and execution. Editing cancels active computation. Choose SVG or PNG
under Frame format, then Download to save the current frame. PNG pauses playback
at the displayed frame and exports an 800 × 450 image with a black background.
These are still images, not video exports. SVG retains vector formula paths;
PNG includes those paths and the browser's rendered text.

Full LaTeX documents, 3D, updaters, full NumPy integration, and MP4 export
are not implemented. The broader examples directory includes APIs
outside this subset. Unsupported operations report Python errors.

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
