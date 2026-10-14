# Completion evidence and remaining gates

The active request is to continue implementation until Manim support is fully
implemented. Current work is substantive progress, not proof of completion.
The documented architecture remains static browser execution. Whether the final
target is the existing MVP/version 1.0 roadmap or full Manim Community parity
has been asked of the user; do not silently equate the current subset with either.

## Differential testing against Manim Community 0.22 (2026-10-12)

Native runs of lite (NumPy venv) are compared with a Manim Community 0.22 install
(TinyTeX for LaTeX) on per-frame family bounds, root classes, durations and final
state. These are bounds-level checks, not pixel comparisons.

| Corpus | Matching | Remaining differences |
| --- | --- | --- |
| Community docstring examples (273 comparable) | 200 | Text bounds use Liberation Sans metrics (macOS Community uses system fonts); AnimationGroup/FadeTransform Group roots; random examples |
| Feature suites (anims, methods, mobs2, 3D, camera, svg, ...) | ~3,600 of ~3,750 | Mostly the Group-root structure above and boolean-op point order |
| Random animation-chain scenes (anim1-5, 1,294) | 1,267 | Arrow quirks (Wiggle and Arrow.scale re-adding tips every frame), NumberLine/Axes become alignment |
| Random 5-step scenes (long1, 242) | 231 | The same arrow and Axes cases; Community's float overflow in two degenerate cases |
| Random updater scenes (598) | 591 | Self-referential updater feedback with arrows |
| Every animation type on mobjects with updaters (840) | 744 | Group roots (Community measures its Group root with handles), arrows sharing tips between parents |
| Random plotting scenes (550) | 550 | — |
| Random method chains (2,900) | ~2,840 | VGroup own points (lite groups cannot hold path points), Group.restore errors Community raises, NumberLine/Axes become structure |
| Repository gallery (`examples/`, 101 scenes, text excluded) | 92 | Group roots, boolean point order, Community's unseeded stream lines and closed-circle tip overflow |

In the browser (Pyodide, Chromium), 393 of the 395 docstring examples render; the two
failures also fail in Community. Every gallery scene in `examples/` renders in Chromium
without page errors and also runs in Manim Community 0.22. Browser-measured Tex sizes
(including `\\` line breaks inside `\textbf`) match Community within a stroke width;
native runs only estimate formulas before measurement.

## Roadmap acceptance audit (2026-10-08)

| Requirement | Current evidence | Remaining verification/work |
| --- | --- | --- |
| Basic shapes and animations | Python frame tests, SVG renderer tests, Pyodide browser playback; Playwright smoke test (`tests/browser/smoke.cjs`, CI job `browsers`) renders DOT, a Manim/MathTex scene and a NumPy scene in Chromium, Firefox and WebKit (all three pass on Ubuntu CI; Chromium and WebKit also verified locally on macOS, 2026-10-10) | Broader examples across the matrix; real Safari/Firefox releases rather than Playwright builds |
| Worker execution and hard Python timeout | ManimClient deadline/cancellation tests; explicit cancel/retry controls; real in-app browser infinite-loop cancellation, 90-second timeout, valid-scene recovery and DOT switching | Repeat cancellation/timeout/recovery across browser matrix |
| Automatic detection and edit debounce | Literal/comment filtering, manual renderer selector with URL aliases, detector/scheduler tests, browser override/reload/recovery/gallery checks | Live sharing-service checks; broader ambiguous-source coverage |
| Scene selection and URL reload | Source-link snapshots, scene/type/DOT options, shortening failure/deadline/stale-response tests | Live shortening availability |
| Gallery | Bundled catalog, stale-load tests, browser loading | Preserve catalog acceptance as APIs change |
| MathTex | Python/backend/renderer tests, real formula SVG paths and export | Glyph bounds, substring APIs, tracing, broader formula coverage |
| SVG/PNG export for both renderers | Graphviz supports both; Manim exports current SVG or 800 × 450 PNG snapshot, with rasterization failure/cleanup tests | Browser export checks across supported browsers |
| Video export | MP4 (H.264) and WebM (VP9/VP8) via WebCodecs with in-memory muxers; container-structure and pipeline tests; Chrome decode, duration, seeking and cancellation checks (2026-10-10) | Safari/Firefox encoder coverage; audio tracks |
| Offline editing/rendering | Versioned complete asset cache, explicit update/retry UI, offline/partial-cache service worker tests | Real browser disconnected rendering and update/eviction behavior across browsers |
| Mobile-friendly UI | Stacked layout, wrapped code, larger controls, accessible toggle; browser checks at 390 × 844, 320 × 568, and desktop resizing | Native mobile keyboard/device coverage |
| Deployed site | Existing test and GitHub Pages workflows | Check every new commit's CI/deployment and deployed behavior |

Sequential and repeated-object animation now has Succession frame tests covering
stage starts, relative operations, replacement, removal, nested groups, checkpoints,
and terminal holds. Browser gallery playback verified accumulated rotation and
final removal, plus Graphviz after switching. Global numeric depth ordering now has Python/SVG tests and real Pyodide browser
checks across transformed groups, including animated crossings and restoration.
Root bring-to-front/back and clear/reintroduction now have Python tests and
Pyodide browser playback checks. Foreground root APIs now have ordering, release, removal, and atomic validation
tests and local Pyodide checks for promotion, release, transformed group painting,
and cleanup. Group/VGroup composition, indexing/slicing, and family queries now have atomic
validation and frame tests; general geometry-bearing families and scene
restructuring remain implementation work. Scene lifecycle hooks and elapsed sampled time
have Python tests and Pyodide browser checks, including teardown animation.

Corner-path VMobjects now have Python/SVG tests and Pyodide checks for tracing,
movement, vertex interpolation, and cleanup. Unequal connected path/polygon
counts now align through exact cubic subdivision, with tests and local Pyodide
checks for continuous morphing, restored pivots, and the final polygon; connected cubic paths support tracing, parameter sampling,
and equal-count control-point interpolation, with Python/SVG tests and local
Pyodide gallery checks. Primitive circle/ellipse/arc/sector/straight outlines now convert into
this morph pipeline, with Python tests and local Pyodide checks for primitive
transitions, restoration, and the terminal curve. Recursive ordered VGroup alignment now has frame tests for nested/unequal/empty
families, leaf wrapping, copy and sequential restoration. General Mobject family
restructuring remains open. Disconnected VMobject construction, separate SVG
contours and ordered per-contour alignment now support ring-to-outline morphs;
Annulus retains analytical radii for same-type transforms. Automatic contour
correspondence remains open. Raw get/set/append/clear points, subpath append and
copied outline append now have transformed-world-coordinate tests and animate
support. Writable points arrays now behave like Community's buffer; glyph geometry remains open.
Exact pointwise_become_partial/get_subcurve now support transformed geometry,
ordered disconnected contours, closed-outline wrapping and animated replacement.
ShowPassingFlash now travels over exact outline portions, including simultaneous
group highlights and reusable removed objects. Broader partial-creation APIs,
per-child passing-highlight delays and glyph geometry remain open. Smooth/jagged
path conversion now supports open and periodic closed cubic splines.
RoundedRectangle now uses closed cubic outlines for circular/concave corners,
per-corner morphing, path following and restoration; general polygon rounding
and rectangle grids remain open.

NumberLine now supplies linear numeric conversion, ticks, numeric labels,
world-space extrapolation/projection and transform-aware marker updates. Python
checks cover transformed insertion without axis drift, sampling, validation,
length changes and restoration. Axes now combines two NumberLines, with Cartesian
conversion/inversion, batch coordinates, numeric and axis labels, transform-aware
updater geometry and atomic coordinate-label additions. NumberPlane now adds styled major/faded grids, native origin-relative spacing,
transform-aware vectors and bounded subdivisions. Broader coordinate/graph APIs
and nonlinear transform preparation remain open. ComplexPlane now maps complex
values through the XY frame, provides imaginary labels and preserves conjugate
marker alignment during sampled transforms. Complex function warping remains open. ParametricFunction, FunctionGraph
and Axes plotting now support sampled XY curves, default smooth interpolation,
declared discontinuity gaps, graph-input queries and dynamic redraw. Numerical
tangent queries, derivative plots and signed trapezoid antiderivative plots now
cover initial calculus APIs. Riemann rectangles now add signed/gradient cells,
refinement and bounding functions. Secant groups now add labeled horizontal/
vertical changes and an extended line, including dynamic redraw. Continuous area
polygons now add changing bounds and gradients between curves, with browser
playback and export checks. Disconnected region topology and adaptive/symbolic
analysis remain open. DashedLine now adds individual straight dash families,
endpoint transforms and orthogonal coordinate guides, with frame and browser
checks for moving markers and rotating axes. DashedVMobject now adds exact cubic
subcurves, approximate equal-length/parameter spacing, phase wrapping, clipping
and disconnected contours, with gallery frame and browser checks. Arrow tips,
glyph paths and general geometry-bearing source families remain open. TangentLine
now follows supported world-space path geometry with clipped finite differences,
length-driven redraw and browser checks. Line angle/length/slope controls now have
anchor, animation, validation and tiny-span tests.

Full Community parity additionally requires general geometry/path morphing, full scene-family
composition and layering, 3D cameras and advanced camera APIs (2D settings, moving-camera pan/zoom and automatic bounds fitting now have Python/SVG tests), glyph-level text/TeX
semantics (basic DecimalNumber/Integer numeric labels now implemented), broader updater utilities (Mobject callbacks, real ValueTracker always_redraw and TracedPath now implemented), graphing, 3D, rendering/video output, and broad API/package
compatibility. These are not implemented or proven by the current tests. Keep
the original requested scope open until its requirements are clarified and
verified; successful individual feature commits do not close the overall goal.


Angle, RightAngle and Elbow now add signed quadrant-selected marks, optional dots,
construction-time queries and moving-line redraw. Angle now owns its editable
cubic path with the optional dot child, with own-point queries and restored
path/dot morphing. Glyph-level family semantics remain open.


ArcBetweenPoints now supplies signed minor/major endpoint arcs, signed-radius
construction, moving endpoints and straight-path transitions. Full 3D arc and
curved-arrow families remain open.


ArcPolygon and ArcPolygonFromArcs now compose closed cubic outlines and retained
arc children, with gap bridges, per-edge styles and filled morphing. Rendering,
Create and Transform now include own geometry and descendants. Automatic edge correspondence and general scene restructuring remain open.


Common Mobject child mutation and self-inclusive split/index/slice APIs now support
ordinary geometry-bearing shapes, with recursive point-family filtering and
point-free container rendering. Glyph/tip point families, general scene restructuring remain open.


Own-plus-child union bounds now support boundary queries, relative layout and
camera fitting. Child attachment/removal/replacement preserves every family's
affine geometry. Conservative rotated/control-point bounds, glyph metrics and
native world-space child coordinates remain open.
Direct child motion inside transformed ordinary shapes, Group and VGroup now
preserves parent outlines and stationary siblings, including nested families,
coordinate helper decorations and frame snapshots.


Group/VGroup arrangement now supports transformed families with nonzero signed
scale, screen-space direction/buffer/aligned edges, fixed first-child placement
without centering and animated position interpolation while retaining parent
pose. Zero-scale arrangements and native world-space child coordinates remain
unimplemented. Conservative bounds and general family restructuring remain open.


Group/VGroup grid layout now supports inferred/explicit rows and columns, all
eight flow orders, variable cell sizes, separate gaps, cell and row/column
alignment, transformed families, animation and restoration. Python tests cover
ordering, incomplete grids, spacing, negative scales and atomic validation; local
Pyodide playback covers reflow/restoration/removal. Ordinary geometry-bearing parent layout is now supported; zero-scale layout
and native world-coordinate semantics remain open; this does not implement Rectangle's internal grid-line geometry.


Mobject now provides common direct-child row/grid layout and arrange_submobjects,
including geometry-bearing parents and point-free containers. Python tests cover
own-outline preservation without centering, world-space gaps, inherited methods,
child identities, copying/checkpoints, atomic validation and animated frames.
Local Pyodide playback verifies a fixed own-outline corner during grid/row changes,
restoration and complete family removal. Zero-scale and glyph/native world-point
semantics remain open.


Standalone triangular/filled triangular/stealth arrow-tip objects now have editable
closed paths, styles, point/base/vector/angle/length properties, family layout,
transforms, morphing and restoration. Python tests and Pyodide playback verify
queries and marker tracking. Arrow now attaches real tip children with start/end tip management, sampled shaft
trimming, fixed-size standalone scaling and endpoint editing. Circular/square
outline and filled tips now have editable geometry and both-end attachment.
General Arc/Circle tip attachment, native world-coordinate child semantics and full tip-family
compatibility remain open.


DoubleArrow now constructs real tips at both ends, with independent tip shapes,
existing Arrow sizing/endpoint transforms and tip-management semantics. Tests
cover both-end marker/shaft alignment and checkpoint restoration. Native
world-coordinate children remain open.


CurvedArrow/CurvedDoubleArrow now provide XY endpoint arcs with tangent-aligned
real tip children, sampled shaft fitting, endpoint/center transforms and existing
family morph/restoration flow. Generic Arc/Circle tip APIs, native world-coordinate
children, arbitrary 3D and full tip-bearing path semantics remain open.


Straight/curved connectors now accept tip_style and provide detached tip creation,
positioning and tip_width controls. Default filled triangular widths follow native
factory/style precedence and short-arrow caps. Generic TipableVMobject inheritance,
Arc/Circle tip APIs and native world-coordinate child semantics remain open.


TipableVMobject now shares XY path-tip factories and management across Line,
Arc and Circle. Generic open/closed attachment and family restoration have
regression coverage. Native world-coordinate children, full mutable-tip path
semantics and arbitrary 3D remain open.


Circle now inherits Arc, supplies XY three-point circumcircle construction,
wrapped angle-based path queries and center motion. Numerical and animation
regressions cover boundary markers during transformed playback and restoration.
Circle surround/stretch, 3D circumcircles and native world-coordinate children
remain open.


Uniform XY dimension fitting/replacement and Circle.surround now provide
geometry-preserving size controls and dynamic surrounding outlines. Regression
coverage includes family bounds, signed transforms, child identities, atomic
validation, animated fitting and updater playback. Nonuniform stretching, full
3D dimensions and native world-coordinate children remain open.


Nonuniform XY vector-family stretching now enables stretching fits, replacement
and surrounding. Regression coverage includes nested signed poses, exact world
point mapping, line endpoints, curved shafts/tips, coordinate conversion,
identities, failure atomicity, animation and restoration. Glyph/camera/shared
family stretching, 3D and native post-deformation tip reset remain open.


Matrix, point and complex-function maps now share vector-family traversal, preserve
separate contours and bend cubic controls during nonlinear deformation. Regression
coverage verifies exact transformed controls, pivots, nested identities, callback
domain/validation, animated interpolation, restoration and tip-bearing connectors.
Adaptive nonlinear preparation/inversion, glyph/camera/shared-family mapping,
native NumPy, 3D and post-warp analytical/mutation APIs remain open.


Common positioning (frame edges/corners, alignment, coordinate setters/matching,
edge pivots, flips) and Community's color palette/utilities, gradients, fading and
style matching now have Python tests and a gallery scene. ManimColor objects,
named-color parsing, 3D axes/coordinates and text glyph flipping remain open.


Polygram/RegularPolygram/RegularPolygon/Star/round_corners and the shape matchers
(SurroundingRectangle, BackgroundRectangle, Cross, Underline) now have Python
tests and browser playback. Polygon/Triangle/Rectangle/Square use Community
classes and defaults. Group translation and scaling now keep children in world
space; rotated-group children, Cutout/ConvexHull/boolean operations and
Rectangle grid lines remain open.


Text, DecimalNumber/Integer and MathTex now have Community-calibrated ink bounds
and sizes (Text from Liberation Sans metrics, numbers from TeX glyph layout,
formulas measured by MathJax with a second render pass). Glyph-level text
submobjects, t2c, MarkupText and Paragraph remain open.


Community rate functions, lagged/remover/reversed animations, shifted fades,
Write/DrawBorderThenFill phases, emphasis animations (Circumscribe, Flash,
Wiggle, FocusOn), arc transforms and swaps, targets/ApplyMethod, function
updates, subsets and letter-by-letter text now have tests and browser playback.
Scene add/remove restructuring and in-place member animation follow Community
for identity-pose groups. TransformMatching*, ApplyWave and Homotopy remain open.


NumPy is available as `np` (lazy Pyodide package) and preview APIs accept NumPy
arrays/scalars. `points` and `get_points()` arrays write back on item assignment,
in-place arithmetic and `out=` ufuncs (views included), like Community's points buffer.


Brace family, Tex (text mode via MathJax), Title, BulletedList, Vector,
LabeledDot, Variable and always_* helpers are implemented with Manim 0.22
reference checks. The default frame (14.22 × 8), stroke widths and anchor/handle
bounds rules now follow Community. ArcBrace, Tex environments and full LaTeX
text macros remain open.


Multi-part MathTex (indexing, tex-based coloring/opacity, isolated substrings),
TransformMatchingTex and TransformMatchingShapes are implemented with browser
part measurement. Glyph-level submobjects inside parts remain open.


Functional/pointwise animations (ApplyMatrix, Homotopy, ApplyWave, PhaseFlow,
ChangeDecimalToValue, …) and labeled connectors are implemented with tests.


Matrix family, get_det_text, Table family and Paragraph are implemented with
Community reference checks; glyph stretching is axis-aligned only.


Glyph-level Text (indexing, t2c/t2w/t2s/t2f/t2g, gradient), MarkupText basics
and per-glyph Write/AddTextLetterByLetter are implemented with Community glyph
position checks.

BarChart and PolarPlane are implemented with Community reference checks;
nonlinear polar warping (`apply_complex_function` on planes) remains open.

VectorField, ArrowVectorField and StreamLines are implemented with Community
reference checks for positions, colors and traced lines. 3D arrow fields and
spatial StreamLines (z_range/three_dimensions) follow Community, including 3D
vector tips. Raster background images and per-pixel stream coloring remain open;
frame size limits dense stream fields.

ConvexHull, Cutout, TangentialArc, ArcBrace, VDict, ScreenRectangle family,
VectorizedPoint, ComplexValueTracker, UnitInterval, CurvesAsSubmobjects,
LaggedStartMap, MaintainPositionRelativeTo, Blink, Broadcast, SpiralIn and
AddTextWordByWord are implemented with Community reference checks where the
output is deterministic.

Graph and DiGraph are implemented with networkx/Community layout parity for the
deterministic layouts; SciPy-based layouts are unavailable. Sources that mention
networkx/nx load Pyodide's networkx wheel by URL (without matplotlib), so
Graph.from_networkx and networkx generators run in the browser.

Union, Intersection, Difference and Exclusion are implemented with Community area and
bounds checks; coincident curved (non-straight) boundaries are approximate.

Code is implemented with Community geometry checks (0.001 units) and Pygments colors;
code_file reads files written to Pyodide's file system; custom Pygments Style classes from
user code remain unsupported.

SVGMobject/VMobjectFromSVGPath (markup strings) and ImageMobject (arrays/data URIs/files) are
implemented with Community geometry/style checks; file paths read files written to Pyodide's
file system. Gradients/patterns, clip paths and image pixel interpolation in Transform remain open.

TypeWithCursor/UntypeWithCursor, AnimatedBoundary, ChangeSpeed, ImplicitFunction,
LabeledPolygram, ShowPassingFlashWithThinningStrokeWidth and FadeTransformPieces are
implemented with Community checks for timing, cursor placement and pole positions.

ManimColor/HSV/RandomColorGenerator, LogBase/LinearBase axes and TeX numeric units are
implemented with Community checks.

Point clouds, Add, ShowPartial, sections/skip_animations, scene updaters, wait_until,
replace, TexTemplate stubs and CoordinateSystem are implemented; audio and
subcaptions are recorded only.

- ZoomedScene (vector inset views, Community frame/display geometry and per-frame aspect sync) is implemented; pixel-level camera images (`get_pixel_array`) are not.
- VectorScene and LinearTransformationScene are implemented (matrix, inverse and nonlinear plane transformations, ghost vectors, labels); Community's mid-animation arc positions are matched numerically.
- ManimBanner, SampleSpace, TransformAnimations and Community's utility functions are implemented.
- Scene code now sees members of posed families (arrow tips, rotated number lines and axes,
  children of transformed shapes) in world coordinates for queries, edits, copies and reference
  arguments, and play() animates such members (Transform targets, .animate, MoveToTarget,
  updaters following them); removing one splits its family with the rest kept in place.

- ThreeDAxes (z axis, shaded axis pieces, 3D labels, coordinate inversion), plot_surface
  colorscales, 3D parametric curves and in-plane-axis Rotate are implemented with Manim 0.22
  checks. 3D frames are projected, shaded and depth-sorted by the renderer from world-space
  leaves, so camera moves reuse pooled geometry; text in 3D is an upright billboard and sheen
  is not modelled. Polyhedra, 3D text planes and OpenGL-only surfaces remain open.
- Polyhedron, Tetrahedron, Octahedron, Icosahedron, Dodecahedron and ConvexHull3D match
  Manim 0.22 geometry (vertex dots, face counts, bounds, vertex-driven face updates).
- 3D frames whose solids move by an affine map (Rotate, rotating updaters) reuse earlier
  geometry with a per-frame transform; a corpus polyhedron scene went from 60 MiB to 14 MiB.

Community docstring corpus (2026-10-09): of Manim 0.22's 395 `.. manim::` docstring
examples, Community renders 372 here (with TinyTeX) and manim-lite renders 376; only the
planar graph layout (2 examples) fails in lite where Community succeeds. Matched behavior
includes play/wait frame timing, static waits, pointwise rotation interpolation, live
Succession, custom Animation subclasses, glyph-level MathTex, text/formula point maps,
networkx-exact spectral and Kamada-Kawai layouts. Remaining diffs are platform font
metrics, MathTex sizes before browser measurement, unseeded random layouts and
Community's AnimationGroup scene-group quirk. Still open: planar layout, Typst/MathTypst,
Succession with lag_ratio != 1, GrowFromEdge default edge, MultiCamera.

Corpus update (2026-10-10): the docstring corpus (414 extracted examples) and the Manim
0.22 documentation gallery/tutorial/guide examples (75) both run with no lite-only
failures; the only lite failures are Typst/MathTypst, which also need the optional typst
package in Community. Formula sizes were compared with browser MathJax measurements fed
back as math_metrics. Newly matched: MathTex/Tex part semantics of 0.22 ({{ }} parts,
isolated substrings as glyph groups, exact-match coloring, multi-part Tex), Succession
lag_ratio, Grow point_color, path functions (utils.paths), planar layout (networkx-exact),
8-cubic arcs, nested ReplacementTransform, DecimalNumber edge_to_fix, second-tip placement
on curved arrows, the isosurfaces quadtree for ImplicitFunction, Computer Modern kerns,
ligatures and interword glue for Tex text, TeX-style fractions, align*/gather* rows,
LaTeX logos, CJK in formulas, nested-svg delimiters, LabeledDot sizing, MarkupText
wrapping/justify and planar 3D text. Remaining diffs: platform font metrics for Text, the
\xrightarrow widths (AnimationGroup draw order now follows Community's scene group). Typst/MathTypst are now
compiled in the browser by typst.ts (matching Community bounds and selections with native
Typst SVG); \_, the color libraries, quaternion utilities, RendererType/QUALITIES,
Section, Camera/MultiCamera and Scene(camera_class=..., random_seed=...) were added. With
these, lite runs 406 of the 414 docstring examples (the other 8 also fail in Community)
and all 75 documentation examples.

Frame-level comparison (2026-10-10): a scene updater recording the scene's bounds every
frame was run on all docstring examples in both libraries. It found and fixed:
SpinInFromNothing's spiral path, compounding tips on scaled DiGraphs, interpolated glyph
indices during transforms, partial Create/Uncreate geometry seen by updaters, Swap of a
group, 0.22's opacity-based ShowIncreasingSubsets/ShowSubmobjectsOneByOne, and unbounded
glyph shear under ApplyWave. Remaining per-frame differences come from platform text
fonts, unseeded random layouts, glyph-level (rather than outline-point) nonlinear maps,
updaters reading a source mid-TransformMatchingTex, and reusing a group after Unwrite.


API surface (2026-10-10): Community's public method lists were diffed class by class
against lite. Added Mobject/VMobject point and curve utilities (curve functions and
lengths, anchors/handles, subpath splitting, smooth/quadratic/cubic path builders,
put_start_and_end_on, reverse_points/repeat, align_data/align_submobjects, insert,
surround, space_out_submobjects, proportion_from_point), rgba style accessors with a
get_style/set_style round trip, the animation override registry (override_animation,
add_animation_override) and Community's isinstance tree (VGroup, Text and MathTex are
VMobjects; FadeIn/Rotate/Indicate are Transforms; arrows are named Vector). Default stroke
widths now match Community (4 for arcs, lines and VGroups; 2 for NumberLine/axes; shaft-
limited DoubleArrow). AnimationGroup now has Animation's accessors and timing builders;
Transform exposes create_target/target_mobject and a path_func separate from numeric
path_arc; Write/DrawBorderThenFill expose get_outline/get_stroke_color; plus Wiggle pivots,
Line.set_path_arc, Arc.stop_angle, MathTex.index_of_part/sort_alphabetically and NumberLine
label/tip getters. The docstring corpus frame comparison now matches 197 of 273 examples.
SpecialThreeDScene works (Manim 0.22's own constructor fails), and the OpenGL point clouds
(DotCloud, TrueDot, OpenGLPMobject...) and pixel cameras (MappingCamera, SplitScreenCamera,
OldMultiCamera) are importable names that raise a clear NotImplementedError. Manim's
example_scenes/basic.py runs completely; its non-TeX scenes match Community frame by frame.
Scene.compile_animations, add_mobjects_from_animations, validate_run_time and
get_moving_and_static_mobjects follow Community, and play() accepts lists and generators.
Still open: frame-loop Scene internals (compile_animation_data, update_to_time),
some CoordinateSystem helpers, TexTemplate preamble attributes, pixel images
(get_image/show raise NotImplementedError) and alternative cameras.

Community module tests (2026-10-10): Manim 0.22's own pytest suite (tests/module, 655
tests) was run against lite through a `manim` shim. Lite now passes 573; the failures are
private internals (_get_subdivision_matrix, _locate_first_match, compile_animation_data,
caching/hashing), file-system TeX/Typst output, OpenGL metaclasses, intentional floating
rounding and point-alignment differences. This pass added Community's ManimColor value
semantics and operators, animate builders and run-time validation, subcaptions, Graph/Matrix/
DecimalNumber attributes, Text font_size/submobjects, Tex separators, TexTemplate body/
environment generation, config.tex_template, manim.utils.unit (Pixels, Percent, Degrees,
Munits), manim.typing aliases, get_quadratic_approximation_of_cubic and empty containers
that ignore shifts. Later passes added Community's per-subpath align_points, NumberLine
add_tip/pop_tips (the family squeezes toward the tip base as in Community), xy-plane
Angle checks, Scene.restructure_mobjects and inert config names.

Manual animation protocol (2026-10-10): `anim.begin(); anim.interpolate(alpha); anim.finish()`
now works without a scene for built-in animations, AnimationGroup (Community's begun/finished
masks) and Succession, and Transform subclasses may override create_target (the target is
optional). A constructor-default diff against Manim 0.22 found PURE_YELLOW defaults for
Indicate, Flash, Circumscribe and FunctionGraph, now matched.
A default-instance diff (color, stroke, fill, size and family of every Mobject class built
with no arguments) then aligned standalone arrow tips with Community's construction, and
manual groups accept mobject-free Wait members.
A constructor-structure diff then gave NumberLine Community's scene view: own points are
the shaft cut at the tip base, submobjects are the tip/ticks/labels, and the default tip
is an ArrowTriangleFilledTip. The internal shaft child remains in `get_family`.
Circles and arcs now sample `point_from_proportion` on their cubic outline (as Community
does), a non-default `num_components` sets circle bounds and rotated centers from its
anchors, and `round_corners` rejects radius lists that do not tile each vertex group.
Point equality follows np.allclose for non-finite coordinates, and importing
`manim.utils.rate_functions` exposes the easing functions kept only in that module.
A submodule import scan (every public class/function Community defines per module) now
finds only renderer, file-writer and interactive-scene internals missing.
A signature scan (keyword parameters of every exported class, function and method) now
differs only in three internal hooks (interpolate_submobject variants, MultiCamera).
Plain Group/Mobject boundaries (critical points, centers, container scale/rotate pivots
and next_to targets) include Bezier handles as in Community; VGroup keeps anchors.
Fuzzing also found two deferred structural differences: Community cuts an arrow shaft
once when its tip is attached (now matched with frozen shafts, see below), and become keeps
extra degenerate children from submobject alignment (now reproduced for scene-code become).
Removing an arrow tip directly now leaves the shaft cut, scene-code get_family matches
Community (no NumberLine shaft), and become raises Community's errors for Group/Mobject
receivers and VMobject-to-Mobject targets. Community 0.22 also fails restore() on a Group or
ValueTracker through the same path; Lite keeps restore working.
become (and so Transform completion) keeps attributes that scene code added, fixing the
LinearTransformationScene gallery example's second transformation of a labelled vector.
shift takes several vectors, space_out_submobjects shrinks members about their world centers
(rotated Axes), arrange_in_grid places cells up and right from the origin as Community does
(visible for shapes with their own outline) and raises ZeroDivisionError with no members.
Members attached to or released from a scaled parent change pose only, so arrows keep their
world-size tips (Arrow.scale's fixed-size tips no longer apply to re-posing).
Arrow shafts are now cut once, as in Community: moving, removing, arranging or spacing out
tips leaves the shaft where it was cut, and add_tip, pop_tips, put_start_and_end_on and
Arrow.scale re-cut it. A stretched tip's `base` is its length-weighted midpoint, as in
Community. NumberLine tip edits follow the same model, so n2p tracks a moved tip and a
removed tip leaves the shaft cut. Remaining fuzz mismatches are mostly become structure.

Scene-code become reproduces Community's align_data padding, so receivers keep their larger
family (faded or point members) with Community's child counts and order. Transform completion
and text/SVG families still use Lite's structure. Seeded fuzz runs now differ in a handful of
programs per 400 (mostly DoubleArrow edge cases and nested become inside arranged families).


VectorField.get_colored_background_image now returns Community's sampled Pillow
RGB image, usable directly in ImageMobject. Worker dependency detection, exact
sample coordinates/colors, limits, serialization and advected-marker cleanup have
regression coverage. Raster painting inside vector paths, per-pixel StreamLines
coloring and pixel cameras remain unfinished.


Raster-colored vector fills/strokes and flat StreamLines now use screen-aligned
PNG paint with shared SVG filters and pooled frame strings. Regression coverage
checks source/style preservation, failure atomicity, transformed geometry,
per-frame image sharing, animation cleanup and exported pixel colors. Pixel cameras,
exact Cairo antialiasing/transparent-raster arithmetic and complete spatial-stream
color parity remain open.


Vectorized field gradients now return NumPy RGBA arrays and load the browser
package on demand. Spatial StreamLines sample all cubic anchors rather than eight
positions along a chord, and use the ordinary sheen-direction gradient. This
matches Cairo's color construction; projected spatial gradients and exact Cairo
pixel arithmetic still require parity work.


Spatial path gradients now carry sampled world-space endpoints through camera
projection, including depth-directed sheen and shaded corner rules. Projected
color placement has regression coverage for ordinary, fixed and pooled rigid
geometry. Exact shading at both corners, glyph-family gradient bounds and Cairo
pixel parity remain open.


The renderer now shades both native corners and uses the native two-row RGBA
selection for fill/stroke/background strokes. Solid shaded shapes also carry
corner gradient endpoints. Cube lighting colors agree with the independent Python
camera hook. Glyph-family bounds and exact Cairo pixel parity remain open.


2D gradients now use current rotated family bounds and invert the object's pose
for local SVG paint. Background-only gradients get endpoints, background RGBA
arrays preserve all stops, and gradient fades no longer square the opacity factor.
A browser SVG-to-canvas halfway-fade pixel check covers the rendered result.
Separately posed ancestor gradients, exact animated bounds and Cairo pixel parity
remain open.
