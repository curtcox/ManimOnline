# Completion evidence and remaining gates

The active request is to continue implementation until Manim support is fully
implemented. Current work is substantive progress, not proof of completion.
The documented architecture remains static browser execution. Whether the final
target is the existing MVP/version 1.0 roadmap or full Manim Community parity
has been asked of the user; do not silently equate the current subset with either.

## Roadmap acceptance audit (2026-10-08)

| Requirement | Current evidence | Remaining verification/work |
| --- | --- | --- |
| Basic shapes and animations | Python frame tests, SVG renderer tests, Pyodide browser playback | Browser compatibility matrix, broader examples |
| Worker execution and hard Python timeout | ManimClient deadline/cancellation tests; explicit cancel/retry controls; real in-app browser infinite-loop cancellation, 90-second timeout, valid-scene recovery and DOT switching | Repeat cancellation/timeout/recovery across browser matrix |
| Automatic detection and edit debounce | Literal/comment filtering, manual renderer selector with URL aliases, detector/scheduler tests, browser override/reload/recovery/gallery checks | Live sharing-service checks; broader ambiguous-source coverage |
| Scene selection and URL reload | Source-link snapshots, scene/type/DOT options, shortening failure/deadline/stale-response tests | Live shortening availability |
| Gallery | Bundled catalog, stale-load tests, browser loading | Preserve catalog acceptance as APIs change |
| MathTex | Python/backend/renderer tests, real formula SVG paths and export | Glyph bounds, substring APIs, tracing, broader formula coverage |
| SVG/PNG export for both renderers | Graphviz supports both; Manim exports current SVG or 800 × 450 PNG snapshot, with rasterization failure/cleanup tests | Browser export checks across supported browsers |
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
support. Full NumPy semantics, mutable points attributes and glyph geometry remain open.
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
path/dot morphing. Mutable NumPy points and glyph-level family semantics remain open.


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
arrays/scalars. In-place mutation of NumPy point arrays remains unsupported.


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
reference checks for positions, colors and traced lines. Raster background
images, 3D fields and per-pixel stream coloring remain open; frame size limits
dense stream fields.

ConvexHull, Cutout, TangentialArc, ArcBrace, VDict, ScreenRectangle family,
VectorizedPoint, ComplexValueTracker, UnitInterval, CurvesAsSubmobjects,
LaggedStartMap, MaintainPositionRelativeTo, Blink, Broadcast, SpiralIn and
AddTextWordByWord are implemented with Community reference checks where the
output is deterministic.

Graph and DiGraph are implemented with networkx/Community layout parity for the
deterministic layouts; SciPy-based layouts and networkx graph objects are unavailable.

Union, Intersection, Difference and Exclusion are implemented with Community area and
bounds checks; coincident curved (non-straight) boundaries are approximate.

Code is implemented with Community geometry checks (0.001 units) and Pygments colors;
code_file and custom Pygments Style classes from user code remain unsupported.

SVGMobject/VMobjectFromSVGPath (markup strings) and ImageMobject (arrays/data URIs) are
implemented with Community geometry/style checks; file paths, gradients/patterns,
clip paths and image pixel interpolation in Transform remain open.

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
- ManimBanner, SampleSpace, TransformAnimations and Community's utility functions are implemented; queries on children of posed shapes still return parent-local coordinates.

- ThreeDAxes (z axis, shaded axis pieces, 3D labels, coordinate inversion), plot_surface
  colorscales, 3D parametric curves and in-plane-axis Rotate are implemented with Manim 0.22
  checks. 3D frames are projected, shaded and depth-sorted by the renderer from world-space
  leaves, so camera moves reuse pooled geometry; text in 3D is an upright billboard and sheen
  is not modelled. Polyhedra, 3D text planes and OpenGL-only surfaces remain open.
- Polyhedron, Tetrahedron, Octahedron, Icosahedron, Dodecahedron and ConvexHull3D match
  Manim 0.22 geometry (vertex dots, face counts, bounds, vertex-driven face updates).

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

