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
