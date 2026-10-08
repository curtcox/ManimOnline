# Agent orientation

## Goal and current state

Build a browser experience for editing Manim source and previewing animations,
while preserving the existing Graphviz editor. This is a static GitHub Pages
site; the established direction is in-browser Pyodide and a limited Manim-lite
compatibility layer, not a server running full Manim Community.

## Read first

1. `README.md` for local serving instructions and public status.
2. `index.html` for editor setup, rendering integration, and output controls.
3. `src/manim-lite.py` for the compatibility API and timed frame generation.
4. `src/unified-worker.js` and `src/manim-client.js` for execution and deadlines.
5. `src/manim-renderer.js`, `src/manim-player.js`, and `src/detector.js`.
   `src/render-scheduler.js` coalesces editor/scene edits and cancels stale callbacks.
   `src/share-links.js` snapshots local share links and bounds optional shortening.
6. `docs/rendering.md` for current gaps and next milestones.
   `src/examples.js` contains the editor gallery catalog and stale-load protection.
   `src/manim-math.js` prepares vector formula glyphs for playback and SVG export.
   `src/manim-export.js` rasterizes current-frame PNG snapshots with bounded loading.
   `offline-assets.js`, `service-worker.js`, and `src/offline.js` manage offline files.
   Bump `OfflineAssets.VERSION` whenever a listed local asset changes, including
   `index.html`, runtime scripts, or gallery sources, to avoid serving old cached code.
7. `examples/multiple_scenes.py` for selection and geometry transform checks.
8. `examples/creation_and_rotation.py` for stroke creation and orbital motion.
9. `examples/layout_scene.py` for relative positioning and animated arrangements.
10. `examples/staggered_scene.py` for overlapping animation timing and cleanup.
11. `examples/path_scene.py` for transformed paths and center-following motion.
12. `examples/arc_scene.py` for open circular paths and signed sweeps.
13. `examples/growth_scene.py` for geometry growth and staggered shrink removal.
14. `examples/style_scene.py` for independent style channels and group opacity.
15. `examples/restore_scene.py` for checkpoint restoration and zero-size recovery.
16. `examples/indicate_scene.py` for temporary highlights and staggered emphasis.
17. `examples/copy_scene.py` for retained sources and independent target cleanup.
18. `examples/connector_scene.py` for transformed endpoint queries and animated connectors.
19. `examples/math_scene.py` for formula rendering and changed-formula crossfades.
20. `examples/succession_scene.py` for consecutive repeated-object animations and cleanup.
21. `examples/layer_scene.py` for global depth ordering across transformed groups.
22. `examples/order_scene.py` for root reordering, clearing, and reintroducing objects.
23. `examples/lifecycle_scene.py` for setup, teardown, and sampled scene time.
24. `examples/corner_path_scene.py` for straight-segment VMobject tracing and deformation.
25. `examples/foreground_scene.py` for grouped foreground overlays, release, and cleanup.
26. `examples/bezier_scene.py` for cubic tracing, parameter sampling, restoration, and mixed paths.
27. `examples/morph_scene.py` for unequal path alignment, restored pivots, and closing outlines.
28. `examples/shape_morph_scene.py` for primitive outline conversion and restored native geometry.
29. `todo/master_plan.md` and the other `todo/` documents for background plans.
    `docs/completion.md` tracks the remaining acceptance gates.

`ace/`, `viz-global.js`, and `svg-pan-zoom.min.js` are vendored dependencies.
Avoid editing these to implement Manim features. The Markdown files under
`examples/` illustrate the broader Manim API; they do not imply browser support.

Read `examples/group_morph_scene.py` for recursive family morphing, unequal child
counts, restoration, and removal. Alignment is snapshot-only; live children keep
existing completion/copy semantics.

Read `examples/group_family_scene.py` for indexing/slices, validated composition,
child removal/reordering, and whole-group animation. Group and VGroup share the
existing container serialization; slices share child identities but no parent
transforms. Do not bypass validated setters when adding family links.

Read `examples/camera_scene.py` for isolated config, square preview resolution,
per-frame backgrounds, and configured SVG/PNG export. Camera metadata is captured
with each frame; preserve default 800 × 450 behavior and per-source reset.

Read `examples/moving_camera_scene.py` for animated pan/zoom and saved-view
restoration. Camera frame roots participate in animation scheduling but are omitted
from display geometry; capture must use their sampled state, including held stages.

## Implementation guidance

- Keep the edit → render → preview loop central. Preserve DOT rendering, sharing,
  and exports when changing the unified flow.
- Extend the existing static architecture before introducing another stack.
  Full Manim, video encoding, LaTeX, and offline support are not proven here.
- Preserve the explicit Render animation/Cancel render controls and their stale-result guards.
- Keep Python execution in a worker so a main-thread timeout can terminate
  runaway code. A Promise timeout inside a blocked worker cannot interrupt it.
- Isolate each source execution namespace and ignore stale render results.
- Keep the compatibility layer in one source rather than divergent copies in
  the page and worker. Label supported behavior and unsupported features plainly.
- Use official Manim/Pyodide documentation when investigating compatibility.
- Keep generated media, caches, and temporary test output out of Git.
- Do not introduce accounts, sharing services, or server infrastructure unless
  the task calls for them. If a server is later introduced, submitted Python
  requires runtime isolation, resource limits, and per-job artifact storage.

## Verification and handoff

Run `python3 -m unittest discover -s tests -v` and `node --test tests/*.test.js`.
Serve locally with `python3 -m http.server 8000`. Check both a DOT graph and a
Manim example in a real browser. Syntax checks or native Python tests do not
prove Pyodide loading or browser playback. Report which checks actually ran.
Update the README and these notes when adding test commands or changing the
runtime. Do not claim full Manim compatibility from a subset implementation.

Read `examples/auto_zoom_scene.py` for combined camera fitting, single-object
focus and restoration. Margin adds to the chosen full frame dimension; preserve
inclusive visibility filtering, pre-mutation validation and deferred animation.
Framing uses existing geometry bounds; text glyph measurements remain open.

Read `examples/updater_scene.py` for timed callbacks, sampled-object following,
camera tracking, and callback cleanup. Keep callbacks out of frame JSON and expose
animation samples through original identities only for the update pass. Restore
live animated geometry in finally; preserve source callbacks during transforms.

Read `examples/value_tracker_scene.py` for shared animated values, callback ordering,
and consecutive relative increments. Trackers participate in timeline/updater
sampling but stay invisible in root and grouped rendering. Preserve finite real
validation and identity for in-place arithmetic.

Read `examples/redraw_scene.py` for factory-driven geometry, suspension/resumption,
and freezing callbacks. become must preserve source callbacks/checkpoints and
independent target geometry. Redraw copies update the callback argument; do not
capture a fixed original object in the regeneration callback.

Read `examples/numeric_scene.py` for DecimalNumber/Integer tracker labels,
formatted intermediate animation values and restoration. Numeric labels use
centered SVG Text, not native TeX digit families. Keep formatting options
independent of numeric interpolation and preserve atomic finite-value validation.

Read `examples/trace_scene.py` for TracedPath sampling, timed dissipation,
freezing and removal. Exclude traced_point_func from snapshots, preserve the
original sampled source identity, and bake current path transforms before
appending world-space points so earlier vertices retain their position.

Read `examples/ellipse_scene.py` for elliptical path motion, primitive morphing
and restoration. Ellipse dimensions are local geometry; preserve exact rotated
bounds, angular outline queries, and independent X/Y radii during cubic alignment.

Read `examples/sector_scene.py` for Sector/AnnularSector signed sweeps,
connected outline following and unequal-curve morphing. Preserve native inner-arc,
radial-edge, reversed-outer-arc and closing-edge order; zero inner radius is valid.
Sectors serialize through the existing bezierpath pipeline.

Read `examples/annulus_scene.py` for separate full-ring contours, outline motion,
radius interpolation and restoration. Preserve opposite winding and separate SVG
subpaths; never insert a radial connector. Ring-to-outline morphs now align contours separately.

Read `examples/rounded_rectangle_scene.py` for circular/concave corner following,
per-corner morphing and restoration. Radii repeat starting at the upper-left;
the path starts at the upper-right. Clamp each cut to half the shorter side and
pin cubic joins exactly so the existing renderer closes the outline without seams.

Read `examples/subpath_scene.py` for disconnected construction and ring-to-outline
morphs. Pending anchors live in vertices on bezier paths; append consumes them.
Aligned snapshots keep integer subpath_lengths to preserve coincident boundaries.
Subdivide contour pairs independently and collapse missing contours at the last
endpoint; never bridge disconnected contours with an SVG segment.

Read `examples/point_array_scene.py` for raw cubic construction, world-space
point queries, animated handle edits and copied outline append. Validate array
length/XY coordinates before mutation; bake transforms before raw appends or
start_new_path so changing bounds cannot move earlier geometry. Returned points
are independent lists; NumPy indexing and mutable points attributes remain open.

Read `examples/partial_curve_scene.py` for exact subcurve extraction, closed-loop
wrapping and animated partial replacement. Partial fractions allocate by cubic
index, unlike distance-weighted path following. Preserve contour boundaries and
receiver styles/callbacks; split control points exactly before baking world coordinates.

Read `examples/passing_flash_scene.py` for ShowPassingFlash, simultaneous group
highlights and sequence reuse. Clip snapshot copies; keep group pivots fixed as
child bounds change. Validate every outline before introducing a group, remove
the flash at completion, and retain its live geometry for subsequent animations.

Read `examples/number_line_scene.py` for NumberLine numeric coordinates, labels,
marker updaters and saved-view restoration. NumberLine serializes through the
group renderer; shaft/ticks/numbers/tip roles identify children without storing
Mobject references in frame JSON. Conversions apply both shaft and parent
transforms, including temporarily exposed animation samples. When adding world
decorations, invert the parent transform and compensate for its changed bounds
pivot; existing geometry must stay fixed. Plotting is described below.

Read `examples/axes_scene.py` for Cartesian conversion, numeric labels and
coordinate-driven geometry during animation/restoration. Tag child axes instead
of serializing object references. Compose NumberLine-local queries with the Axes
parent transform; actual child getters retain local group semantics. Coordinate
inversion solves the current XY basis, and label insertion compensates for the
parent's changed bounds pivot after validating both axes. NumberPlane is described below; this example uses an explicitly sampled polyline.

Read `examples/plot_scene.py` for sampled scalar/parametric plotting, dynamic
coefficients, exact graph-input queries and closed-loop drawing. Exclude function
providers from JSON but retain them in copied runtime objects. Validate/bound all
sample counts before invoking callbacks, and commit generated points only after
successful sampling. Smooth contours independently with natural open ends or a
periodic closed system; pin rounding-close seam anchors. Preserve transforms and
compensate changed handle bounds so animated smoothing cannot move anchors.
Declared gaps create separate contours; do not bridge discontinuities. Sampling
is explicit rather than adaptive, and full graphing/NumPy semantics remain open.


Read `examples/plane_scene.py` for NumberPlane grids and vectors following a
transformed coordinate frame. Grid geometry stays in Axes-local coordinates;
keep faded/background groups before the axes and tag their roles rather than
serializing Mobject aliases. Preserve native origin-relative spacing, omitted
outer boundaries and default unit lengths. Bound subdivision counts before
allocating geometry. Nonlinear transforms and preparation remain open.


Read `examples/complex_scene.py` for complex coordinate conversion, imaginary
labels and conjugate markers during plane transforms. n2p/p2n compose the inherited
XY frame. Label queries produce world-positioned independent geometry; attachment
inverts the parent transform and compensates its changed bounds pivot. Exclude
unattached `_coordinate_labels` aliases from JSON; attached label getters find
role-tagged children so become/copy/restore cannot leave stale object references.
Keep per-label formatting options independent so imaginary units do not leak
onto real labels. Nonlinear complex warping remains open.


Read `examples/calculus_scene.py` for coordinate-relative graph queries, numerical
slopes, derivative/integral plots and a moving tangent/readout. Finite differences
operate in numeric coordinates, independently of axis pose. Reject a dx that
cannot change the input instead of silently reporting a zero slope. Numerical
integration uses signed trapezoids from zero and validates every scalar/result.
Plot count validation must still happen before invoking providers. Plotting gaps
do not remove integral-domain singularities; adaptive/symbolic calculus remains open.


Read `examples/riemann_scene.py` for signed Riemann cells, coarse/fine group
transforms and a bounding function. Keep Rectangle identities while serializing
four polygon corners in the current axes basis. Preflight ranges, counts and
styles before callback sampling; no source graph/axis mutation. Preserve native
open partition ends, left-input bounding baselines and signed color inversion.
Cell colors support hex gradients; continuous regions are described below.


Read `examples/secant_scene.py` for interval refinement and moving labeled secants.
Keep the native world-horizontal/vertical triangle convention on rotated axes.
Component getters must find role-tagged children rather than stale object aliases.
Supplied label Mobjects are copied. Font shrink/spacing uses explicit estimates;
do not claim measured glyph layout. None/zero dx defaults to a tenth of the range;
negative intervals reverse sides, and zero changes collapse labels. Use redraw
for changing inputs; check final removal and both MathTex labels in Pyodide.


Read `examples/area_scene.py` for get_area, moving integration bounds and gradient
fills between curves. Keep Community's sampled control-point Polygon convention,
exact provider endpoints, zero baseline and bounding-range intersection. These
polygons bridge declared plot gaps; do not claim disconnected/singular topology.
Validate ranges/styles before callback endpoints. SVG gradient IDs must be unique
across shapes and frames, with local inert defs retained in SVG/PNG exports.


Read `examples/guides_scene.py` for DashedLine and coordinate projections.
Dash families serialize actual Line children with no hidden object aliases.
Preserve child edits during endpoint transforms; recompute count only through
regeneration. Preflight finite lengths/ratios and the 1000-dash cap. Orthogonal
projections use current world shaft endpoints, including extrapolation, independent
axis rotation and collapsed shafts. Copy guide configs before applying overrides.
Use tracker/function inputs directly when two redraw callbacks must agree in the
same frame; scene updater ordering can otherwise leave a one-frame lag.


Read `examples/dashed_paths_scene.py` for DashedVMobject, periodic phase, approximate
arc-length spacing and parameter spacing. Preserve exact cubic cuts and separate
contours; length lookup excludes contour jumps. Bound requested counts and sampled
lookup work before constructing children. Keep styles on independent copied
subcurves, with no stored source aliases or lookup tables in JSON. Closed full
coverage and open shifted-end clipping need explicit edge-case tests. A Line
converted to a cubic subcurve must query its actual path endpoints. Arrow tips,
glyph geometry and general geometry-bearing source families remain open.


Read `examples/tangent_paths_scene.py` for TangentLine, finite path sampling and
length-driven redraw. Use clipped path proportions and the sample chord midpoint,
with no retained source-object alias. Reject unresolved/coincident samples and a
full closed-path chord before treating rounding noise as a direction. Normalize
components directly so valid tiny spans do not overflow a reciprocal. Line angle
changes default to the start; length changes default to the center. Preserve
NumberLine's existing positive-length contract and the animated set_angle entry.


Read `examples/angle_scene.py` for signed Angle sweeps, quadrant selection,
optional dots, RightAngle and Elbow. Angle owns its cubic arc/corner path with
only the dot as a child, using geometry-bearing family rendering.
`get_value` stores the construction-time sweep. Rebuild with `always_redraw` for
moving lines. Defining line references are excluded from frame JSON; preserve
that isolation when extending serialization. Parallel/zero-span lines are empty.


Read `examples/endpoint_arc_scene.py` for ArcBetweenPoints, signed angle/radius,
moving endpoints and a zero-angle straight transition. Endpoint arcs reuse Arc
and the existing partial/morph pipeline; zero-angle/coincident cases use a
polyline. Start/end queries delegate to Mobject so analytical arc geometry does
not fall through VMobject's corner-only getters. Keep endpoint precision checks,
finite XY validation and less-than-full-turn limits explicit.


Read `examples/arc_polygon_scene.py` for ArcPolygon, ArcPolygonFromArcs, filled
closed outlines, independent edge styles and geometry-bearing families. `.arcs`
is a property of children, avoiding stale runtime aliases after copy/become.
The closed outline is copied at construction; editing a child does not rebuild
it. The SVG collector now paints own geometry plus descendants, preserving
ancestor transforms/opacity and global leaf depth. Create traverses both own
paths and children. Transform plans independently align both portions. Preserve
DOT and ordinary VGroup behavior when extending this shared path.


Read `examples/angle_path_scene.py` for own-path queries, movement, dotted-angle
to corner morphs and restoration. Defining line references are exposed via
`.lines`/`get_lines` but excluded from frame JSON. Keep the own path independent
of dot geometry when editing or extracting points. Mutable NumPy point arrays and glyph-level family geometry are still open.


Read `examples/shape_family_scene.py` for common Mobject child mutation, nested
geometry-bearing families, late attachment, removal and restoration. Common child
validation/mutators now live on Mobject. Group retains child-only indexing;
ordinary geometry-bearing objects split/index themselves before their children.
Point extraction governs family_members_with_points and own-member inclusion;
glyph-level families remain unsupported. Empty Mobject roots are invisible but
render descendants. Preserve cycle/camera-frame checks and snapshot isolation.

Transform completion now uses become to preserve ordered source-child identities
and callbacks. Keep that behavior: later remove(original_child) must work after
parent animations. has_no_points and get_group_class accompany family slicing.


Read `examples/family_bounds_scene.py` for own-plus-child bounds, public boundary
queries, camera fitting and distant child insertion/removal. `_own_local_bounds`
contains primitive geometry; `_local_bounds` unions it with child bounds.
`_replace_children` compensates changed pivots on all families by shifting
A(delta)-delta. Exact text/rotated curve bounds remain open.

Read `examples/child_motion_scene.py` for moving children inside rotated/scaled
ordinary shapes. Also read `examples/group_motion_scene.py` for nested Group and
VGroup motion, insertion and removal. `_family_pivot_cache` tracks own/child bounds and the previous
local pivot; changed child bounds with unchanged own geometry compensate position
by A(delta)-delta. Synchronize before pose changes and frame serialization; exclude
the cache from JSON. Explicit child replacement resets the cache to avoid double
compensation. Preserve sampled-frame pinned pivots. Coordinate helpers now use the common
compensation; do not reintroduce their former manual pivot shifts.
Native world-space child coordinates remain open.


Read `examples/transformed_layout_scene.py` for arrangement after rotation and
nonzero scaling. Mobject.arrange composes temporary world-space child poses, uses
next_to on those copies, and inverts only the resulting translation vectors.
Retain the live parent pose and child identities so animated layout does not
introduce additional rotation or scale interpolation. Validate all translations
before editing live children, synchronize pivot compensation, then optionally
center. Zero-scale groups cannot invert their transform and remain unsupported.


Read `examples/grid_layout_scene.py` for animated grid reflow and restoration.
Group/VGroup grid layout supports dimension inference, all eight fill orders,
cell and row/column alignment, separate gaps and optional measured cell sizes.
`_layout_targets` composes world poses; `_apply_layout_targets` validates and
inverts translations for both row and grid layouts. Retain parent angle/scale,
child identities and starting center. Validate dimensions/options before changing
children; cap grids at 1000 cells. Collapsed families remain unsupported. `animate.arrange_in_grid` uses the existing morph flow.


Read `examples/shape_layout_scene.py` for child rows/grids on transformed ordinary
shapes, corner invariance and restoration. Layout helpers and public arrange/
arrange_in_grid now live on Mobject; Group inherits them. Always use direct
children, not split()/iteration, which include the own outline for ordinary
shapes. arrange_submobjects delegates dynamically to arrange and is supported
in .animate chains. Preserve parent outlines with center=False; optional
centering intentionally translates the whole family. Grid preserves family center.


Read `examples/tip_geometry_scene.py` for standalone editable tip outlines and
live point/base queries during morphs. ArrowTip is an abstract VMobject base;
ArrowTriangleTip/ArrowTriangleFilledTip and StealthTip supply closed corner paths.
Tip base queries use the midpoint of the ordered cubic array, not distance-based
path sampling, and tip_point uses the first path point. Stealth length is 1.6
times its base-to-tip span. Triangle angles are reduced to a stable trig phase
before constructing distinct vertices. Arrow attachment is now implemented for straight Line/Arrow families.


Read `examples/arrow_tips_scene.py` for real tip children, fixed-size scaling,
endpoint edits, replacement and restoration. _refresh_tip_shafts runs on ordinary
serialization and sampled Scene.capture overrides; always derive shaft endpoints
from the current tip geometry, not interpolated stale metadata. _tip_role marks
structural target child slots during interpolation. explicit_tips suppresses the
legacy renderer head even after pop_tips. Logical endpoints include tip points;
own Arrow points describe the shaft. Native world-coordinate child semantics and
curved tip-bearing paths remain unfinished. NumberPlane vectors force buff=0.


Read `examples/round_square_tips_scene.py` for circular and square tip attachment
on animated arrows. Circle tips hold eight editable cubic segments; square tips
hold four corner segments. Circle length sets diameter and start_angle sets its
first anchor. Square length sets side length, inherited tip length measures the
diagonal, and start_angle is metadata (native constructor does not pass it to
Square). Preserve the anchor order: shaft bases use the ordered curve midpoint.
Both filled/outline variants flow through existing family/path rendering.
