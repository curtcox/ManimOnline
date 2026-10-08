# [ManimOnline](https://curtcox.github.io/ManimOnline)

A web-based editor that supports both Graphviz DOT language diagrams and Manim Python animations, with automatic detection and appropriate rendering.

## Features

- **Graphviz DOT Support**: Full support for Graphviz DOT language diagrams
- **Manim-lite animations**: In-browser Python execution with SVG frame playback, play/pause, replay, and seeking
- **Auto-Detection**: Automatically detects whether input is DOT or Manim Python
- **URL Sharing**: Share diagrams via URL parameters
- **Export**: Download diagrams as SVG or PNG

## Usage

Visit the deployed site and start typing:
- For Graphviz: Write DOT language code (e.g., `digraph { a -> b }`)
- For Manim: Write a `Scene` subclass with `from manim import *` (see the supported subset below).

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

## Supported browser animation subset

Python runs in a Web Worker using Pyodide 0.27.0. The browser loads Python on
first use, so the first render needs an internet connection. This is a small
Manim-like runtime, **not the full Manim Community engine**.

- Shapes: `Circle`, `Arc`, `Dot`, `Square`, `Rectangle`, `Line`, `Arrow`, `Triangle`, `Polygon`,
  `Text`, and `VGroup`.
- Scene operations: `add`, `remove`, `play`, and `wait`.
- Animations: `Create`, `Uncreate`, `Write`, `FadeIn`, `FadeOut`, `GrowFromCenter`,
  `GrowFromPoint`, `ShrinkToCenter`, `Rotate`,
  `Rotating`, `MoveAlongPath`, `AnimationGroup`, `LaggedStart`, `Transform`, and
  `ReplacementTransform`; chained `.animate.shift()`, `.move_to()`,
  `.set_color()`, `.set_fill()`, `.set_stroke()`, `.scale()`, `.rotate()`,
  `.next_to()`, and `.arrange()`.
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
available in this runtime. Arrow shafts and heads reveal together. Transforms
interpolate matching geometry and crossfade between different shape types.
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
whole added group or keep its children as separate scene objects. `Succession`
and repeated-object sequences within one play remain unsupported.

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

Animation previews run at
15 frames per second and are limited to 60 seconds, with a 90-second deadline
for loading and execution. Editing cancels active computation. Download saves
the current SVG frame, not a video.

LaTeX/`MathTex`, 3D, updaters, full NumPy integration, MP4 export, and offline
caching are not implemented. The broader examples directory includes APIs
outside this subset. Unsupported operations report Python errors.

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
