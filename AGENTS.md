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
 `src/manim-video.js` encodes all frames with WebCodecs and muxes MP4/WebM in memory;
 timestamps come from frame indices, never wall-clock time. Keep moov before mdat.
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
`tests/browser/smoke.cjs` (Playwright; CI job `browsers`) renders DOT and Manim in
Chromium, Firefox and WebKit; see README for the local command. Playwright's
Firefox build may fail to launch on recent macOS ("Could not find profile folder").
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
independent target geometry. As in Community, the always_redraw callback rebuilds the
original object (a closure), even when run on a copy, so animation copies keep their shape.

Read `examples/numeric_scene.py` for DecimalNumber/Integer tracker labels,
formatted intermediate animation values and restoration. Numeric labels are one
centered SVG Text leaf until indexed/iterated; then `_explode` builds Community's
per-character glyphs (`_NumberGlyph`, presented as MathTex, `_tex_glyph` serif layout
from `_numeric_boxes`) and set_value rebuilds them (`_number_exploded` keeps the leaf pose). Keep formatting options
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
start_new_path so changing bounds cannot move earlier geometry. Scene code gets
`points`/`get_points()` as LivePoints ndarrays (`_point_array(owner=...)`): item writes,
views and `out=` ufuncs call set_points in world coordinates. Inside the library
get_points still returns lists; arithmetic results are plain arrays.

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
transforms and a bounding function. Keep Rectangle identities; each cell is Community's
axis-aligned box around its two baseline corners and graph point (even on rotated axes). Preflight ranges, counts and
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
of dot geometry when editing or extracting points. Glyph-level family geometry is still open.


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
Scene code sees children in world coordinates (see the world-call notes at the end).


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
before constructing distinct vertices. Standalone tips follow Community's construction:
triangles are BLUE and resized about their bounding-box center (center x = -0.25 for
start_angle=PI); stealth tips scale about (0.4, 0). Attached tips are positioned by
tip_point, so keep near-zero chords (closed paths) guarded with relative tolerances.
Arrow attachment is now implemented for straight Line/Arrow families.


Read `examples/arrow_tips_scene.py` for real tip children, fixed-size scaling,
endpoint edits, replacement and restoration. _refresh_tip_shafts runs on ordinary
serialization and sampled Scene.capture overrides; always derive shaft endpoints
from the current tip geometry, not interpolated stale metadata. _tip_role marks
structural target child slots during interpolation. explicit_tips suppresses the
legacy renderer head even after pop_tips. Logical endpoints include tip points;
own Arrow points describe the shaft. Native world-coordinate child semantics and
general Arc/Circle tip attachment remains unfinished. NumberPlane vectors force buff=0.


Read `examples/round_square_tips_scene.py` for circular and square tip attachment
on animated arrows. Circle tips hold eight editable cubic segments; square tips
hold four corner segments. Circle length sets diameter; like Community, circle
tips are RED and always start at angle 0 (start_angle becomes 0). Square length sets side length, inherited tip length measures the
diagonal, and start_angle is metadata (native constructor does not pass it to
Square). Preserve the anchor order: shaft bases use the ordered curve midpoint.
Both filled/outline variants flow through existing family/path rendering.


Read `examples/double_arrow_scene.py` for DoubleArrow with independently configured
tip_shape_start/tip_shape_end, both endpoint markers and restoration. DoubleArrow
subclasses Arrow and retains frame type arrow; never introduce a second renderer
implementation. tip_shape_end overrides tip_shape; start shape defaults separately
to filled triangle. Both tips use the existing role tags and sampled shaft bases.


Read `examples/curved_arrow_scene.py` for CurvedArrow/CurvedDoubleArrow. These
subclass ArcBetweenPoints but materialize raw cubic geometry and mark
_curved_tip_path. _refresh_tip_shafts fits shaft_curves from raw endpoints to
sampled tip bases; never feed fitted curves back into raw alignment. Renderer and
own-path queries consume fitted curves, logical endpoints use actual tip points.
Orient tips from endpoint minus adjacent raw handle. Curved scaling includes tips
and endpoint fitting transforms the whole family uniformly. Collapsed curves
cannot expand by endpoint fitting. Preserve the stored local arc center.


Read `examples/tip_style_scene.py` for tip_style, tip_width and detached factories.
Line.get_unpositioned_tip merges generated styles then copied tip_style; exact
ArrowTriangleFilledTip gets generated width from tip_width/default tip length.
create_tip compensates parent scale and position_tip uses the existing local
orientation helper (local frame); scene calls go through `_scene_tip_call`, so
scene code receives and passes detached tips in world coordinates, as in Community.
Neither attaches children. add_tip reuses them and supplied
tip objects keep their style/size. CurvedArrow inherits these helpers and initializes
its copied style mapping before attachment. get_tip can return a lone start tip;
role-specific tip/start_tip properties require the matching attached role.


Read `examples/generic_tips_scene.py` for Arc/Circle attachment. TipableVMobject
owns common factories, management, tangent orientation and logical endpoint APIs.
Arc/Circle/Line inherit it. Generic attachment materializes raw local cubics and
compensates pivot changes before adding the tip family; preserve existing world
geometry. Open shafts use the same _curved_tip_path fitting pipeline as curved
arrows; exactly closed paths retain their full raw outline (zero chord).


Read `examples/circle_construction_scene.py` for Circle.from_three_points,
point_at_angle and arc-center motion. Circle now subclasses Arc but retains frame
type circle. Keep point_at_angle as wrapped point_from_proportion so edited paths
and signed transforms behave consistently. Three-point construction normalizes
chords before solving the XY circumcenter; do not square raw large coordinates.
Reject duplicate/collinear/3D or nonfinite geometry explicitly. Circle validation
now occurs at construction through Arc, including radius=None's unit fallback.


Read `examples/surround_scene.py` for uniform XY fitting and Circle.surround.
Mobject.rescale_to_fit uses current family dimensions and scale; zero dimensions
remain a no-op. replace captures target center/length before mutating the source.
Circle.surround computes the diagonal directly rather than first fitting the
chosen dimension: vertical/horizontal line targets must not cause premature
collapse. Preserve child identities, signed pose and target geometry. Nonuniform
stretch flags fail explicitly until the runtime can represent family stretching.


Read `examples/stretch_scene.py` for nonuniform XY vector-family deformation.
Mobject.stretch copies source/target, composes every old ancestor transform,
maps world geometry and stores identity poses relative to mapped parent origins.
Keep object/child identities through become; preserve disconnected contours and
pending anchors. Curved tip-bearing paths bake displayed shafts and disable the
similarity refit after nonuniform deformation. _stretch_baked marks canonical path
snapshots for Transform interpolation/restoration. Unsupported glyph/camera/shared
families must fail before changing live geometry. Stretched surround follows
native target aspect ratio then diagonal-width fitting; it can be an oval.


Read `examples/point_map_scene.py` for matrix/point/complex maps. _apply_xy_map is
shared with stretch; linear maps keep straight/polyline/polygon types, nonlinear
maps materialize their cubic controls. Do not map just polygon vertices and discard
warped handles. Nonlinear callback traversal must not evaluate synthetic container
origins, which may lie outside the callback domain. Matrix/function defaults are
ORIGIN; stretch defaults to the family center. Explicit real arrow children allow
Arrow-to-cubic alignment; legacy snapshots without explicit_tips retain their
prior morph behavior. Post-warp endpoint/tip edits and analytical centers remain
implementation work; native NumPy and 3D are not supplied by these APIs.


Read `examples/positioning_scene.py` for frame-edge placement, alignment, flips,
gradients and fades. align_on_border reads the module `config` at call time (it is
reset per render). Coordinate helpers use critical points and reject nonzero z.
rotate(angle, axis): OUT/IN only, except a half turn about an in-plane axis, which
delegates to apply_matrix as a reflection. Palette values come from Community's
manim_colors; colors are plain hex strings, not ManimColor. Gradient helpers treat
Text/MathTex leaves as painted members even though they have no path points.


Read `examples/polygram_scene.py` for polygrams, stars, round_corners and shape
matchers. One vertex group stays type `polygon`; several use bezierpath with
subpath_lengths. Rectangle/Square subclass Polygon but keep analytical types;
VMobject._materialize_path converts analytical outlines before raw path edits.
Mobject._world_container: identity-pose Group/VGroup/Mobject containers pass
shift and scale to children (world coordinates); exact Group/VGroup/Mobject also
pass rotation, so plain groups never hold a pose. Subclasses (NumberLine, Axes,
...) keep their pose. Transform interpolates differing poses with `_lerp_pose`
(complex scale*e^(i angle) lerp), which equals Community's pointwise straight_path;
only Rotate/Rotating turn rigidly. Mobject._to_local_pose converts world-placed
members before attaching to a transformed parent; turn about the pivot itself,
since a world container's bounds center is not rotation covariant.


Read `examples/text_layout_scene.py` for measured text, numbers and formulas.
Text em = font_size/72 (Pango at 96 dpi), TeX em = font_size/96 — both measured
with Manim Community 0.22; do not reintroduce the old font_size/50 scale.
_text_layout builds ink-centered lines from _SANS_GLYPHS (Liberation Sans) or
_CM_GLYPHS (DecimalNumber); Scene.render attaches it as `layout` after capture and
the renderer pins tspans with textLength. MathTex sizes come from per-render
math_metrics (browser getBBox); unknown formulas are estimated and reported in
math_estimated, and index.html re-renders once with measurements.


Read `examples/animation_tour_scene.py` for rate functions, lagged animations,
emphasis effects, arc swaps and targets. Animation._member_states implements
Community's lag sub-alphas over _painted_paths; fades use nested=False to avoid
compounding SVG opacity. Use Animation._complete (finish + remover) wherever an
animation is completed. Scene.add/remove use Community restructuring and
Scene._introduce only adds absent mobjects; capture() draws animated members
inside their on-screen group, so Scene.validate rejects members of non-identity
pose groups. play(rate_func=...) assigns animation.rate_func before prepare.


NumPy: validations use _REAL (numbers.Real) / numbers.Integral, never (int, float),
so NumPy scalars work; Vector normalizes scalars and render_scene's JSON default
handles leftovers. The worker loads NumPy only for sources mentioning np/numpy
(networkx/nx sources load networkx by wheel URL, avoiding its matplotlib lock dependency; PIL sources load Pillow);
OfflineAssets.optional caches these wheels without making them readiness requirements.
Renderer gradients thin color lists above 256 stops to evenly spaced stops.
When NumPy is loaded, `_scene_call` returns Vector results to scene code as mutable float
arrays (Community's type); without it scene code gets Vector (tolist/copy/shape only).
Coordinate entry points accept arrays via `_listed`. Tests compare points through
`PointTestCase`, which turns arrays into tuples.


Read `examples/annotation_scene.py` for braces, Title, Tex, bullets and Variable.
Default frame height is 8 (Community). Renderer strokes are local-unit widths
in scene units (they thicken under camera zoom, as in Cairo); keep inheritedScale threading in renderMobject.
_BOUNDS_WITH_HANDLES is set by get_width/get_height and by _critical_point on
non-VMobject families (Group/Mobject use all points, as in Community, so their
centers and container pivots include handles); internal pivots use anchors. get_center may differ from _pivot_point for rotated outlines; use
_pivot_point in transform math. Scenes see the arrow as `Vector`; internally
`Vector` is the coordinate tuple — never shadow it. A Manim 0.22 reference venv
can be built with pango/TeX packages to check geometry numerically.


Fidelity guard: tests/fixtures/community_reference.json holds Manim 0.22 bounds
for 27 snippets; add a case (and regenerate with the fixture's generator script)
when changing geometry, layout or bounds behavior.


Read `examples/formula_parts_scene.py` for multi-part MathTex. Parts are
_MathTexPart children (type mathtex, `part` index) of a vgroup-typed MathTex; all
share one \class-tagged expression string. Keep _class_wrap producing valid TeX.
Metrics may be [w, h] or [w, h, parts]; interpolate keeps `part` discrete.


Read `examples/text_effects_scene.py` for glyph-level Text. Text._explode turns a
text leaf into a vgroup of single-glyph Text children (pose moved onto glyphs,
_char_index kept) only when indexed/iterated or styled per glyph; keep leaves
unexploded otherwise to limit frame size.
Glyphs (with _char_index) never explode again; they iterate as [glyph] like Community's.

Read `examples/chart_scene.py` for BarChart value changes and PolarPlane azimuth
labels. PolarPlane.get_vector takes plane coordinates (as in Community), not world
points; use pr2pt with an Arrow from get_origin for polar vectors. Keep radius
numbers attached once: get_coordinate_labels returns the axis like Community, but
add_coordinates only adds the azimuth group, avoiding duplicate family members.

Read `examples/vector_field_scene.py` for arrow fields, nudged particles and
stream flow. Preserve `_PCG64` parity with NumPy's default_rng; Community's
StreamLines noise depends on it. Add the StreamLines object to the scene before
start_animation (its updater drives flow). Keep `_flow_points` out of frames and
add lines with one `add(*lines)` call; per-line adds recompute family bounds
quadratically. Use `_snapshot_copy` instead of copy.deepcopy for snapshot dicts.

The worker transfers pooled frames (`render_scene(..., compact=True)`, expanded by
`expandPooledScene`); repeated snapshots and large arrays become shared objects.
Never mutate frame data in the page, renderer, player, math or export code.
`tests/unified-worker.test.js` covers the decoder; a Python test checks that the
expanded pooled output equals plain render_scene output.

Read `examples/effects_scene.py` for hulls, cutouts, tangent arcs, arc braces and
attention effects. Nonlinear maps must keep Community's 1%-handle derivative rule;
tests compare against `community_mapped`. VDict keeps `submob_dict` (excluded from
frames) and still accepts plain Mobjects in add/remove for group internals.
UpdateFromFunc animations complete last in play(). Succession runs live: each
stage is prepared on the real scene when the previous one completes (Community's
update_active_animation), so stage callbacks may touch live objects.

Read `examples/graph_scene.py` for graph layouts, attached edges and animated graph
editing. Keep `_MT19937`/`_PCG64` exact; layout tests compare against networkx via
Community. Bookkeeping that holds tuples or non-JSON keys goes in `_frame_excluded`.
`become` deep-copies target attributes with a memo mapping replaced descendants to
live members; don't reintroduce stale child references. play() ends with a dt=0
update pass after completion, matching Community: no time passes after the last
frame of a play/wait. A wait with no time-based or scene updaters is static
(int(duration*fps) frames, no updaters); other waits run update(0) first.
Transform runs the mobject's updaters on its start/target copies every frame
(`_advance_copies`), as Community's Animation.update_mobjects does.

Read `examples/boolean_scene.py` for boolean outline operations. The engine lives in
`_boolean`/`_BOOLEAN_RULES`; outputs must stay closed cubic contours with explicit
subpath_lengths. Tests compare areas/bounds with skia-pathops results, not point order.

Read `examples/code_scene.py` for Code listings. The worker loads Pygments only for
sources matching `Code(`; keep `_code_tokens` working without it (plain colors).
Monospace layout depends on `_is_mono(font)` being part of the text-layout cache key.
Pointless members (`_is_pointless`) are excluded from family bounds.

Read `examples/svg_image_scene.py` for inline SVG and pixel images. Keep the renderer's
image href whitelist (inline base64 raster only) and SVGMobject's DTD rejection; both
are security boundaries for shared links. Circle's default color is RED (Community).

Read `examples/typing_scene.py` for typing cursors, animated boundaries, ChangeSpeed and
implicit curves. Use `_points_to_world` for batches of points; per-point
`_point_to_world` recomputes the pivot and is quadratic on long paths.

Read `examples/log_axes_scene.py` for log axes and colors. Colors are ManimColor (a
str subclass); keep `_paint` in color setters. NumberLine.scaling is excluded from
frames; Axes coordinate code must go through `_axis_shift` and the scaling functions.
DecimalNumber units are a `unit_sign` child in local coordinates.

Read `examples/point_cloud_scene.py` for point clouds, Add and sections. Only
`_instant` animations may have zero run_time; capture() drops frames while a section
skips animations. TexTemplate objects are accepted and ignored by MathJax.

Read `examples/zoomed_scene.py` for ZoomedScene. The display is a pure container
(`camera_view`) with a `camera_screen` rectangle child and the display frame; capture
syncs the zoomed frame to the display's whole-pixel aspect and writes `camera.views`.
The renderer draws views as clipped, transformed re-renders (no pixels). Assigning
`width`/`height` rescales (Community); write analytical dimensions via `__dict__`.

Read `examples/linear_transformation_scene.py` for LinearTransformationScene. path_arc
is per point in `_arc_geometry` (parent frame, then inverse sampled pose). Scene
updaters run after mobject updaters inside the exposed sample pass. Keep transport
encodings (`$pool`, `$xy`, `$xyz`, `$base`) confined to `_pooled_json`/`expandPooledScene`.
Geometry arrays (`_GEOMETRY_KEYS`) are always rounded and pooled; the rest of such a node is a
shared `$base`, so per-face styles of rebuilt surfaces are sent once.

Read `examples/banner_scene.py` for ManimBanner, SampleSpace and utilities. Mobject.add
adopts world-placed members into posed parents and remove releases them (see `_adopt`,
`_release`); internal code that builds parent-local children must not call add on an
already-posed parent with local coordinates. restore() is become(saved_state).


Read `examples/three_d_scene.py` for ThreeDAxes, plot_surface, solids and camera
motion. ThreeDScene frames hold world-space leaves (`_root_frame_data` flattens each
root; text keeps an `anchor3d`) plus `camera.three_d`; `ManimRenderer.projectThreeD`
shades, depth-sorts and projects them. Keep projection out of Python so static
geometry pools across camera moves. `tests/fixtures/three_d_frames.json` feeds the JS
projection tests; regenerate it with its generator when the frame format changes.
Scene play/wait reuse unchanged roots' frame data (`_static_frames`) only when no user
updaters, scene updaters or UpdateFromFunc animations could edit them; built-in camera
updaters carry `_camera_updater`. 2D Axes ignore a z coordinate, like Community.
Polyhedra keep Community's Graph of Dot3D vertices and a face-rebuilding updater
(`match_points` is family-wise). ConvexHull3D uses a deterministic incremental hull
of outward triangles. get_center/get_critical_point/_z_extent/_handle_bounds share
one bounds memo per outermost query (`_bounds_query`); never mutate geometry inside them.
Batch read-only queries (plot samples) share one memo via `_memo_query`; NumberLine
caches its world frame there. Linear `_apply_xy_map` uses an affine fast path.


Glyph-level MathTex: ManimMath.glyphLeaves extracts MathJax's drawable leaves in TeX's
(dvisvgm) order — mfrac/msqrt/mroot/munderover/mover children are visited in TeX order —
and metrics() reports [w, h, parts|null, glyphs] where glyphs are [cx, cy, w, h, part].
Python keeps formulas whole until indexed: MathTex[i] is a part (`_split_single` gives a
single string its part) and part[j] explodes into `_MathTexGlyph` leaves (`glyph` index,
drawn by the renderer from asset.glyphs). Before measurement `_estimate_glyph_count`
places estimated glyphs and out-of-range indices return placeholders; keep the second
render pass (math_estimated) working. Background strokes (`background_stroke_*`) render
as a stroke-only copy behind the element.

Community docstring corpus: extract every `.. manim::` example from an installed Manim
0.22 and run it through both libraries (dry_run, low quality) to find failures and
compare final bounds/durations; Text bounds differ by platform fonts, so compare them
only on Linux with Liberation Sans. A TinyTeX install provides latex/dvisvgm for the
reference side. For formulas, collect `math_estimated` expressions from a native run,
measure them in the browser with `ManimMath.prepare`/`metrics`, and rerun natively with
those `math_metrics` (the page's second pass); without that, MathTex sizes are estimates.

MathTex follows Manim 0.22: parts are the strings split at `{{ }}` only; isolated
substrings and tex_to_color_map tag glyphs with `\class{manim-sub-k}` (MathJax merges
nested classes into one attribute, so parse class lists) and match exactly. Rows/`&` are
wrapped by `_environment` (align* rows 1.5em, Tex gather* lines 1.2em). Tex text runs use
the cmr/cmbx/cmti/cmtt/cmss TFM kerns, ligature widths and TeX interword glue
(`_kerned_text`); ManimMath.patchFractions lays MathJax fractions out as TeX does.
Text in ThreeDScene is planar: 3D rotations bake into glyph_matrix + glyph_depth and
frames export `plane3d`, which the renderer projects as an affine glyph map.

Typst/MathTypst follow Community 0.22: Python builds the same documents
(`_TYPST_TEMPLATE`, 10pt) and lists missing ones in `typst_pending`; the page compiles
them with typst.ts (`src/manim-typst.js`, lazy CDN WebAssembly) and renders again with
`typst_svgs`. Keep `ManimTypst.clean` stripping typst.ts's style, script and
foreignObject overlays. MathTypst groups come from `hide` probe documents compared by
leaf signature, exactly as Community; a placeholder (and lenient select) covers the
first pass. Imported black members (glyphs or stroked rules) take the mobject color.

AnimationGroup/LaggedStart/Succession reproduce Community's add_mobjects_from_animations
draw order: their non-introducer members (flattened through nested groups) are re-added
in group order before they begin, so they move in front as Community's added Group does.
The preview keeps them as separate roots (no Group root); groups with an explicit
`group=` and internal ones (`_internal`, e.g. ChangeSpeed) are left alone.

World calls: posed families (Arrow, rotated NumberLine/Axes, shapes with children) store
children in the parent frame, and library code relies on that. Calls from scene code
(any file other than manim-lite.py, so tests count too) go through `_scene_call`: the
member is placed in world coordinates (`_enter_world`, pinning posed ancestors' pivots),
the method runs, and it is placed back. Parents are tracked weakly in `_PARENTS`; link
new children (`_link_children`) whenever you assign `children` outside
`_replace_children`. Reference arguments (`_REFERENCE_METHODS`, constructors such as
Brace or Line) get world copies (`_world_view`). play() animates posed members in world
coordinates (`_world_members`) and `_root_states` re-poses their states into the parent
frame; split posed members drawn as roots are posed into the world. Transform targets
are world copies. Inside manim-lite.py, never assume a child query is world-space.
The `Scene.mobjects` setter keeps every root's registered ancestors alive
(`_root_ancestors`): the final capture runs after construct returns, when a split
family's parent would otherwise be collected and its members drawn unposed.

FadeTransform samples two aligned Transform plans (source → fitted ghost, fitted ghost →
target) and returns `_SourceStates`, so updaters see the source half, not the more
visible state. GrowArrow scales tips and shaft width from zero, as Community does.
FadeTransform save_state()s the source when constructed; completion removes it (splitting
parents off the roots), restores it and appends the target. Transform takes
replace_mobject_with_target_in_scene (ReplacementTransform sets it).
subdivide_bezier uses Community's subdivision matrices; internal callers use `_subdivide`
(Vectors). SVGMobject/Code read existing (Pyodide) files through the same parsers/limits.
Tests must pass under plain `python3` without NumPy (the browser's default); use
`point_list` and `HAS_NUMPY` in tests that touch points arrays.

Class tree: VMobject and Animation use the `_CommunityTree` metaclass so scene code's
isinstance/issubclass follows Community (`_VIRTUAL_BASES`: VGroup/Text count as VMobject,
AnimationGroup as Animation, FadeIn/Rotate/Indicate/... as Transform). Inside the library,
type dispatch that depends on lite's real inheritance must use `_is_a(x, VMobject)`.
The arrow class is exposed as `Vector` via __name__. Stroke widths follow Community:
DEFAULT_STROKE_WIDTH (4) for VMobjects/VGroups, 2 for NumberLine and Axes axes.
`tests/test_community_api.py` checks these Community-measured values.

Community module tests (`tests/module` of a Manim checkout, run with lite installed as
`manim`) drove these behaviors: `_validate_children` uses Community's messages and only
accepts (virtual) VMobjects under VMobject/VGroup parents; family cycles stay rejected.
Mobject `__getattr__` provides Community's get_x/set_x compatibility layer, so hasattr
on any `get_`/`set_` name is true. Plain Mobject/Group `set_points` stores bounds-only
`_mobject_points` (never drawn, excluded from frames, disables `_world_container`).
NumPy scene calls return lists of points as arrays; `c2p(xs, ys)` returns Community's
transposed (3, n) array. Line graphs answer `input_to_graph_point` by binary search.
`.animate` returns an Animate builder (`_built` converts it in play/groups; `.build()`
also sets `mobject.target`). Scene play/wait/pause/wait_until validate run times with
Community's messages (sub-frame values warn and clamp); empty AnimationGroups construct,
are not `_instant`, and raise only when begun. Overrides may define `finish(self, scene)`.
ManimColor stays a hex `str` but follows Community values: equality between colors is
RGBA closeness (plain strings still compare as text), hash is the hex with alpha, and
arithmetic/bitwise operators work on RGBA. Integer indices return float channels while
slices keep str behavior (internal hex parsing slices); check hex with startswith, not
`value[0]`. Non-float tuples are 0-255 channels; to_rgb and the helpers return arrays.
Text.font_size is a property: the unscaled size lives in `__dict__['font_size']` (read it
there inside the library) and the property reports it times |geometry_scale| (Community
derives it from height); setting it rescales. Text/MathTex `submobjects` expand glyphs or
parts on access (internal code uses `children`). Tex typesets arg_separator inside the
preceding part and collapses whitespace runs as TeX does. PreviewConfig `_PASSIVE` keys
(seed, dry_run, quality, ...) are stored but only seed affects the preview.
`manim.utils.unit` (Pixels, Percent, Degrees, Munits) reads the live config; Pixels use a
1080-pixel-high reference until the scene sets pixel dimensions (`_pixels_explicit`), so
the 800 × 450 preview keeps Community's default pixel sizes. ThreeDCamera's fixed-mobject
collections hold mobjects (dict/set), with orientation callbacks kept by id.
`manim.typing` aliases come from the submodules' module `__getattr__` (`_typing_alias`:
NDArray with NumPy, list otherwise) so annotations and unions work. An empty exact
Group/VGroup/Mobject ignores shift (Community moves points; it has none).
`color`/`fill_color`/`stroke_color` are Mobject properties (`_style_property`): scene-code
assignment calls set_color/set_fill/set_stroke; library code reads and writes the stored
value. Scene reads of `color` use Community's get_color (stroke color when the fill is
transparent). Library code that needs the configured color must read `self.color` (stored).
A VMobject constructor `color=` list is solid in its first color (Community); fill_color/
stroke_color lists and set_color keep gradients, but scene reads of color/fill_color/
stroke_color and get_*_color report the first color (`_one_color`, `_scene_get_*`). Text,
TeX and SVGMobject validate `ManimColor(color)` (lists raise Community's ValueError), and
GrowArrow.begin raises Community's scale_tips TypeError for anything but an Arrow.

VMobject.align_points is Community's per-subpath pairing (trailing null curves dropped,
missing subpaths become null curves at the last point); morph snapshots still use
_aligned_point_lists. Angle and line_intersection reject nonzero z like Community.
PreviewConfig._PASSIVE also lists Community's inert directory/window/flag settings.
NumberLine tips are role-tagged children (`_tip_at_start` marks start tips); add_tip scales
the other children toward the tip base like Community but leaves the shaft (and n2p) alone.
Generic get_<world property>() calls from scene code run through _in_world.
render_scene installs a `manimpango` stand-in (Weight/Style/Variant/Alignment enums,
list_fonts = Text.font_list) only when the real module is not importable.
Manual protocol: built-in animations accept begin()/finish() without a scene (`_scene_optional`)
and interpolate through `_animation_state` from `_manual_start`; snapshot colors go through
`_paint`. AnimationGroup/Succession implement Community's manual interpolate. Transform calls
an overridden create_target at begin. Constructor defaults can be diffed against Manim 0.22
with `inspect.signature`; colors are PURE_YELLOW for Indicate/Flash/Circumscribe/FunctionGraph.
Animation role flags follow Community: Uncreate and ShrinkToCenter are not introducers,
ShowPassingFlash is an introducing remover, and the thinning-flash group is not a remover.
Mobject.get_subpaths covers containers (none) and set_points accepts an empty list on a
pointless container. Unsupported outline types fall back to sampling their own world cubic
points in point_from_proportion (an Arrow samples its shaft, as in Community).

Arc transforms (path_arc) between similar analytical shapes (squares, circles, equal-aspect
rectangles/ellipses) use `_arc_similarity`: each point's arc is a similarity, so pose
interpolation is exact. Other cases still use the point arcs in `_arc_geometry`. Rotated
standalone circles/annuli bound their cubic points like other outlines (width counts
handles). LaggedStartMap skips members already covered by an earlier shape's family.
Arrow.scale follows Community's pop/scale/re-add: default pivots come from the logical
endpoints, a zero factor collapses the shaft with put_start_and_end_on and turns tips to
point along -x (zero-direction tips use angle PI), and the width resets from the shaft
between tip bases (`_shaft_length`); put_start_and_end_on does the same. `_link_children`
never relinks a member from a family that still contains it to a plain Group/VGroup/Mobject
(get_tips() built such groups, which broke world calls on tips). `_place` distributes all
three operations to the children of unposed container subclasses so world round trips stay exact.
Non-straight paths (path_arc, spiral_path and other _PointPath functions) act on world points:
_sample_transform passes members `_child_frames` (parent-to-world similarities of the start,
target and sampled parents as `_pose_frame` tuples), and _arc_geometry/_arc_similarity map
through them, so tips of moving arrows follow Community. Straight paths pass no frames.
Growth animations on families with fixed-size arrow tips sample a Transform plan from
copy().scale(0).move_to(point) (ShrinkToCenter: toward copy().scale(0)) instead of scaling.
Family plans (own geometry plus members): a childless side is padded like Community's
get_point_mobject, with collapsed transparent copies at its own center, and each side's
members are re-posed into the frame of the aligned own snapshot (alignment may bake poses).
When a family's own pose turns or scales between start and target (`_turning_pose`), its
members are planned in the parent frame ('group_world' plans, or a 'world' marker on
'family' plans) and `_members_into` re-poses each sample into the sampled parent frame: a
lerped parent pose composed with lerped member poses would curve Community's straight paths.
VMobject.set_points drops `_curved_tip_path`: explicit points are the drawn shaft and tips no
longer refit them (Community). Exposed draw_progress samples cut curved arrows from the
shaft trimmed by their whole tips, computed before the tips themselves are exposed partially.
SpiralIn saves, restores and moves each shape in world coordinates (`_in_world`), so an
arrow's tip spirals with Community's path; get_center_of_mass uses family world points.
Community leaves an arrow's shaft in place when its tip moves alone (see `_shaft_fixed`).
Several animations may drive one object (Community): `Scene._prepare_in_order` applies each
earlier animation's states(0) to the live object (`_sampled_copy(partial=True)` turns
draw_progress into pointwise_become_partial geometry) before preparing the next, as
Community's begin() runs interpolate(0). AnimationGroup.states lets only animations begun
and not finished on the previous update override shared objects; waiting/finished members
rank first. Partly shared families (a group and its member, overlapping groups) are allowed:
`Scene._later_members` splices each live member's state from the latest-ranked override
containing it (overrides order = animation order) and pushes ancestor fade opacity down to
the other members. Restoring animations (`_restores_start`: FadeOut, ShowPassingFlash) reset
the live family to their start on completion when another animation of the play drives it
(`Scene._mark_restores`); groups restore after all members finish, as Community's
clean_up_from_scene runs after finish(). Rotate fixes its pivot at the center when constructed and ignores about_edge;
Rotating resolves about_edge at begin.
TransformMatching*: unmatched targets fade in as a real `_arrivals` VGroup introduced at begin
(Community's FadeIn copy) with one group snapshot; unmatched sources fade out by one shared
shift. When every piece is a childless leaf under identity-pose containers, pieces are folded
back into one snapshot of the source tree so updaters see the whole family.
ShowPassingFlash accepts arrows: families with their own path cut every member with points
via pointwise_become_partial of `_own_outline` (a childless copy keeping the tip-trimmed
shaft). pointwise_become_partial accepts arrows (they become bezierpath shafts), and Line
endpoint getters stay tip-aware after that, so a collapsed arrow keeps Community's length.
Morphing a curved-tip path into a shape without one aligns its drawn shaft (`shaft_curves`,
already in a family's own snapshot) and drops `_curved_tip_path`, so frames interpolate
pointwise like Community instead of refitting to collapsing tips (which diverged). Updater
exposure drops a stale live `_curved_tip_path` when the sampled snapshot lacks it.
`_own_shaft` hoists a NumberLine's identity-posed shaft child into the root snapshot (type
line, ticks as children) when it morphs into a family that is not number-line shaped, so
alignment follows Community's NumberLine (own line points, ticks submobjects).

Same-type primitives keep analytical interpolation unless both their local geometry and
their pose scale/turn differ; then `_align_path_snapshots` aligns them pointwise (Community's
straight path), since lerping radius and scale separately is not linear in the points.
Recursive inversion (`_member_states`) keeps a NumberLine's shaft child first, as its own points.
Animation-driven updaters (`turn_animation_into_updater`) apply `_sampled_copy(partial=True)`:
partly drawn outlines become pointwise partial geometry, so live bounds follow Community.
SVG arcs follow svgelements (`_svg_arc_cubics`): parameter slices of at most 36 degrees as
quadratics with the (4 - cos(step)) / 3 control push, raised to cubics. A DOCTYPE without an
internal subset is stripped before parsing; ENTITY/internal subsets stay rejected.
SVGMobject(color=...) colors only the still-empty group (Community); parsed shapes keep SVG paint.
Config frame_width/frame_height are independent values (Community); `_camera_dict` gives a
scene's camera the configured width with height fitted to the pixel aspect, and cameras (flag
`_camera`) keep width/height coupled. Square pixels therefore give a 14.22 × 14.22 frame unless
frame_width is set, as examples/camera_scene.py does. `frame_size` sets both pixel dimensions.
MarkupText validates like Pango: only Pango tags, matched nesting and no stray `<`; failures
raise ValueError with Community's message.
Community animation internals: Animation/AnimationGroup._setup_scene, Succession.active_index/
active_animation (absent before begin), and animation.total_time as turn_animation_into_updater's
clock. ImageMobject keeps uint8/uint16 pixel arrays (pixel_array_dtype, inverted at that depth);
the drawn PNG is scaled to 8 bits.
Reshaping a curved arrow (reverse_points, or morphing to/from a non-curved path) aligns
the drawn `shaft_curves` pointwise, as Community does, instead of refitting the shaft to
interpolated tips; plain pose changes of curved arrows keep the tip-fitted refit.
DashedLine tips are children tagged `_tip_role`; `_dashes()` excludes them. add_tip refits the
dashes (and an opposite tip) by a similarity about the far end, pop_tips stretches them back
and put_start_and_end_on carries tips along. Endpoints are tip points (Community's quirky
start-tip get_start/get_end are not reproduced). BackgroundRectangle frames carry
`_fill_partial`: Create/DrawBorderThenFill/ShowPassingFlash fade its fill instead of tracing.
Equal total curve counts with different contour splits are not aligned per contour:
Community pairs points in order, so `_align_path_snapshots` cuts both at the union of
their boundaries (e.g. reverse_points on a Cutout). Scaling a planar outline with z != 0
bakes it to a bezierpath; Indicate/FadeIn interpolate through `_snapshot_lerp`, which
plans an alignment when snapshot shapes differ. Fade shifts and growth points accept z.
next_to/arrange accept z directions. World containers (Cube, VGroup) keep XY pivots, so
`_layout_targets` records each target's z-extent midpoint (`_layout_depth`) and
`_apply_layout_targets` shifts by its change. 3D stretch defaults to the center, as
Community. Polyhedron/Graph updaters return early once become() removed their structure.

MovingCameraScene frame updaters run only when the frame is a scene root (added
explicitly or by animating it), as in Community's update_mobjects; never append the
frame to update or static-wait roots implicitly.

`.animate` follows Community's _AnimationBuilder: creation sets mobject.target (clearing
the old one first), build() reads mobject.target, begin copies it. ApplyMethod-style
subclasses (`_builder = False`) still build at begin. Transform also updates its real
target (`_target_source`; TransformFromCopy's is the source). Animations with
`_start_follows_updaters` (Create, FadeIn...) finish as their updated live copy.
wait_until captures the frame before testing stop_condition.
Rotate/Grow*/SpinIn/Indicate keep a `_LiveMorph` (Community's starting and target copies)
only when the family has updaters; Grow/SpinIn/Rotate sample it with their exact path
formulas, because generic point paths do not act on analytical pose-only shapes.
MoveAlongPath defaults to suspend_mobject_updating=False: its live copy moves, then updates.
Layout helpers (arrange, arrange_in_grid, space_out_submobjects) move `_layout_members()`:
a NumberLine shaft stands for Community's own points and stays with the parent. Line and
Arrow get_start/get_end ask an attached tip (its tip_point), never stale endpoint metadata.
API probes (Community vs lite on single expressions) must evaluate in the scene namespace:
EXPORTS plus VectorArrow as Vector and `_user_interpolate` as interpolate (as _render_scene).
PreviewConfig.frame_center exists only on scene cameras (`_camera`); to_dict exports it only
when nonzero so default frames stay unchanged.
Text.text is a property: scene code gets Community's stripped string; library code (and frames,
via __dict__) keep the drawn string. The raw line-spacing multiplier lives in `_line_spacing`;
`line_spacing` reports Community's point pitch. Inside manim-lite.py never assume scene code
sees the drawn string.

Community module tests: copy Manim 0.22's tests/module next to a conftest.py that loads
manim-lite, calls render_scene once (installing the `manim` module) and supplies the config
fixtures, then run pytest with --continue-on-collection-errors. Remaining failures are expected
categories: LaTeX/Typst files, OpenGL, file IO, private helpers, non-finite points and the
preview's fixed 15 fps. Submodule imports serve the flat namespace; capitalized names other
than the color palettes are classes, so missing ones raise ImportError.

`_PathOptions` holds the path keywords for Transform and the animations that accept them.
Analytic shapes follow point paths only through `_arc_similarity` blends (see
`_CirclesPath.similarity_blend`); add a blend rather than moving just the center. prepare()
runs a deep-copied terminal `_complete`, so it replaces instance `_on_finish` callbacks.

Scene-view hooks: `_scene_call` runs `_scene_<name>` (when the class defines it) instead of
`<name>` for scene-code calls, so a class can show Community's structure without changing
library internals. NumberLine uses it: scene code sees own points (the shaft cut at the
tip bases), `submobjects`/iteration/indexing without the shaft child, and Community's
`nl[0] is nl`. Library code keeps using the real `children`, including the shaft.
Scene-code get_family also omits NumberLine shafts. `_scene_remove` on tipped lines bakes
the current shaft cut into the endpoints (Community never regrows a shaft; pop_tips restores
ends explicitly). `_scene_become` raises Community's errors: plain Mobject receivers lack
interpolate_color, and VMobjects cannot become plain Mobjects; library become is unrestricted
(restore, Transform completion).
Shaft cuts: Community cuts a straight/curved shaft once, when tips attach. Lite refits the
shaft to its tips until `_shaft_fixed` is set; `_freeze_shaft` (scene calls that edit a
tip, layout, space_out after scaling, removing a tip) bakes the cut into own start/end or
curves. Re-cuts unfreeze (`_unfreeze_shaft`: add_tip, pop_tips, put_start_and_end_on,
Arrow.scale) and re-aim tips at the restored endpoints. Cuts follow the ordered cubic
array midpoint (`_tip_base`), which affine edits carry along; the public `base` is
Community's length-weighted midpoint, which differs only for stretched tips, so
Arrow.scale freezes at those bases (`_cut_shaft`). Tip getters never freeze.
NumberLine shares the model: its shaft child reaches the tip points (n2p unchanged) until
a tip edit, tip removal or layout freezes it at the tip bases; then `_logical_end` makes
get_start/get_end (and so n2p) follow the tip points, or the cut end once a tip is gone.
Mobject.__setattr__ records attribute names that scene code adds (`_scene_keys`, not in
frames); become keeps them as Community does (its become copies only points and colors).
Scene-code become first pads a copy of the target like Community's align_data
(`_aligned_target`: faded repeats, center VectorizedPoints, and push_self_into_submobjects as a
VGroup of world-view members plus a childless shaft-frozen copy; under posed ancestors the push
falls back to a center point), so receivers keep
the larger structure; library become (Transform completion, restore) does not. Families with
text, SVG or NumberLine scene views are left unaligned (`_alignable`).
Property setters that check their caller must use `_from_scene()`, which skips that frame.

Transform completion becomes `_aligned_target(target)`: the mobject keeps Community's aligned
family (the larger member count, faded repeats/center points) and member point counts (the
member with fewer curves is subdivided; analytic types survive when unchanged), root included:
Create/Uncreate trace by curve index, so later traces follow Community. align_points keeps
explicit subpath_lengths for multi-contour results. Scene become leaves root points unaligned. Uncreate and reversed Write leave the mobject collapsed onto each
outline's first point even when removed (Community's final pointwise_become_partial(0, 0)).
put_start_and_end_on semantics apply to the whole family: pop_tips maps added members with the
shaft onto the tip points, add_tip maps them about the fixed end (Arrow.scale's inner pop and
re-add adds an extra factor when a start tip is added beside an end tip), and Arrow.scale is
Community's literal pop, scale, re-add. `Arc.get_arc_center` is Community's normal-intersection
estimate on the first curve (not the analytic center). Scene-code `.animate` calls run as scene
code (`_call_as_scene`). Fuzzers: ~/tmp/chainfuzz (method chains) and ~/tmp/animchain (scenes).
SurroundingRectangle/BackgroundRectangle measure like Community's Group(*mobjects): all
points, handles included (`_union_bounds(handles=True)`). Updater timing: an animation's
finish resumes its mobject (update(0)) before the scene's update_mobjects(0); nothing runs
after construct returns.
NumberLine get_start/get_end ask an attached tip's point first (also while partially drawn),
so c2p stays fixed during Create(axes), as in Community.
Within one play(), each animation's copies (Community's starting/target copies with
updaters) advance after the earlier animations of that play were sampled for the frame
(`Scene._exposing` + `_expose_snapshot`), as Community's update_to_time interleaves
update_mobjects and interpolate. Skipped sections jump each play/wait to its end in one
update (Community's time progression is [run_time]).
Copies advancing for animation k see animations < k at this frame and the others (k itself
included) at the previous frame, starting from every animation's states(0) (Community's
begin() interpolates to alpha 0). Exposure restores members' `_PARENTS` links afterwards
(partial exposure runs pointwise_become_partial on childless copies); members a sampled
family has beyond the live one are exposed as linked copies of Community's repeat origins
(add_n_more_submobjects puts copies right after each member), and become pads plain-group
receivers the same way. Community updates every animation's starting copy: animations that
sample from `self.original` should use the updated live copy when the family has updaters
(Homotopy, ShowPassingFlash, Rotating about the copy's current center, GrowArrow, and
ShrinkToCenter, whose ScaleInPlace(0) target is not recentred). AnimationGroup updates copies
only of animations begun and not finished, and none for members it suspended before they
began (Community's group.suspend_updating precedes the sub-animations' begin); Succession
updates only the active stage; ChangeSpeed (a plain Animation) always updates its inner one.
ChangeSpeed reproduces np.piecewise exactly, including int truncation when the rate function
returns an int (smooth(1) is int 1, so the animation can finish at its start).
Non-suspending animations (MoveAlongPath, ShowIncreasingSubsets) register in
`Scene._deferred_updates`: their live copy's updaters run during the scene's update pass, in
root order, and the result is re-exposed (`_expose_snapshot(..., again=True)`).
Detached tips from scene-code create_tip/position_tip are in world coordinates
(`_scene_tip_call`). Transform alignment also subdivides tipped straight shafts (cut at the
tips first, `_freeze_shaft`). `_own_shaft` hoists posed straight NumberLine shafts by baking
their pose. FadeIn/FadeOut scale an Arrow's faded copy even by 1 (Arrow.scale re-adds tips).
Wiggle on families with tipped arrows runs live like Community (`_community_style`): each member
is reset to its starting points, then scaled (Arrow.scale re-adds the live tips) and rotated
about the live mobject's center, as scene calls. Other Wiggles keep the sampled pose.
FadeTransform adds its target copy (`_ghost`) as a root after the source while it runs
(Community's Group(source, target copy) root) and draws the target half there.
Differential probes for updaters during every animation type: ~/tmp/updprobe, ~/tmp/updprobe2,
~/tmp/updprobe3 (always_redraw objects as animation targets).
Point clouds keep z: stored cloud entries are [x, y] or [x, y, z] (`_cloud_point`, z only when
nonzero, so 2D frames are unchanged). ThreeDScene frames hold world cloud points that
projectThreeD projects; 2D cameras ignore z like Community's orthographic camera.
Previews allow 120 s / 1800 frames (MAX_FRAMES, `_TOO_LONG`); the worker still rejects results
over 32 MiB. play() sets any keyword on its animations (Community's compile_animations), and
config.frame_rate/renderer are validated and ignored. With NumPy loaded, scene code gets
Community's ndarray results from the space-ops/bezier utilities listed in `_ARRAY_EXPORTS`.
Surface evaluates func under one bounds memo (`_memo_query`) and bakes in place; inside a memo
window Axes.coords_to_point reuses cached axis frames (`_c2p_frame`) with the same arithmetic
order as the uncached path. `_enter_world`/`_exit_world` clear an active memo when they move a member.
Throwaway samples may bake 3D maps in place under `_maps_in_place()` (Rotate's live morph);
`_sampled_copy` shares one memo over its bottom-up walk, dropping each node's position-dependent
`('bounds', id, flag)` entries after its pose fix.
3D arrows: tips with a z direction turn through `_turn_tip_3d` (Community's azimuth rotation,
then a polar tilt; detached position_tip tips level first via `_level_tip` and skip the tilt
once `_init_positioning_axis` is set, which stays out of frames). put_start_and_end_on with z
turns tips by the minimal rotation between the old and new directions. Vector fields read
z_range/three_dimensions (ArrowVectorField keeps output z; StreamLines spatial flows).
Linear 3D maps (rotate, scale, stretch, apply_matrix) pass `matrix=` to `_map_points_3d` and
map points directly, as Community's apply_points_function does; only apply_function uses the
handle-scaling rule. Cone bakes its direction rotations in place. ThreeDScene's
`_root_frame_data` caches world curves by (curve-list identity, pose chain) in
`_emit_cache`, so shared snapshot lists map once and pool once. `Scene._later_members` keeps
a per-frame member index (`_later_index`); Create samples copy nodes with `_node_copy`, which
shares unchanged arrays, so never mutate snapshot lists in place.
`_RigidFrames` compresses ThreeDScene frames: when a root's (or, failing that, a child
subtree's) world leaves are one affine image of an earlier frame's, they reuse that frame's
point lists plus a shared `rigid3d` [3x3 rows, shift] that projectThreeD applies first. Every
point is checked (1e-6); text, clouds, fixed-orientation and z_index_as_group leaves are left
alone. This keeps rotating solids under the worker's 32 MiB limit. A level that misses three
times in a row rests 15 frames (its subtrees still fit) before retrying.
Mobject.__deepcopy__ copies `_POINT_KEYS` lists with `_snapshot_copy` (no per-float memo);
other attributes keep deepcopy semantics. Circle/arc/ellipse/annulus curves come from a
memo (`_ROUND_CURVES`, copied out) and get_points reads `_round_snapshot`, not to_dict.
A negative Arc/Circle/Dot radius is Community's mirrored arc: stored as |r| with start_angle + PI.
SpiralIn applies its two opposite turns as the equivalent translation of each shape's
center of mass (computed once).
Sphere/Dot3D reuse mapped face geometry by `_surface_key` (`_SURFACE_FACES`) unless a subclass
overrides func. proportions_along_bezier_curve_for_point is Community's exact test: per-axis
polynomial roots (`_polynomial_roots`, pure Python) rounded to round_to, intersected.
A VGroup with own points (set_points, set_points_as_corners, append/add_line_to, ...) becomes
native polyline/bezierpath geometry with children, drawn like other geometry-bearing families;
VMobject's point editors are borrowed onto VGroup, and emptying the points restores 'vgroup'.
Arrow semantics in add_tip/Arrow.scale follow the class (isinstance Arrow), not `_type`, since
make_smooth turns an arrow's own path into a bezierpath. Community's Arrow.scale fails with
IndexError on a lone start tip, and scene-code restore() on plain Mobjects (Group,
ValueTracker) raises NotImplementedError; tests use the library restore via `restore_state`.
Every wait()/pause()/play(Wait()) adds the Wait's empty placeholder Mobject as a scene root
before other animations begin (Community's add_mobjects_from_animations), so self.mobjects[-1]
idioms match; capture skips childless plain Mobject roots, so frames are unchanged. Wait's
manual begin/interpolate/finish are no-ops. A FadeIn/Fade copy whose curved-tip flag differs
from its target goes through a transform plan (`_same_shape`), aligning the drawn shaft. A
collapsed (zero-scale) path sample follows path_arc by moving its single point.
Never complete an animation by assigning a deep-copied `__dict__`: members become unlinked
copies (no `_PARENTS`), so scene calls on them skip world placement. Use library become.
`_snapshot_lerp`'s same-shape path applies `_lerp_pose` to every node whose pose turns, so
equivalent angles (differing by 2π, e.g. re-tipped copies) do not spin.
Arrow.scale(0) freezes the collapsed shaft (`_shaft_fixed`): Community never cuts a zero-length
shaft at the tip bases. Line.put_start_and_end_on on a non-line own path (after become/Transform)
regenerates a straight path when the ends coincide exactly, else maps the family generically;
pop_tips materializes analytical own paths first, so Arrow.scale on a morphed arrow follows suit.
Refit arrow shafts whose pose turns and whose local ends change are baked to identity poses in
`_align_path_snapshots`, so their ends move in straight lines. A 2D VMobject family scaled to
zero bakes the collapse into its members (no zero-scale parent pose; tipped families and
coordinate systems excepted). become never transfers tip roles (Community's tip attributes keep
naming the receiver's members): members keep their own roles, new members get none, and when
roles change the receiver's shaft is first frozen at the target's tip bases. Tipped receivers
pad with copies of their own members unless the target is a pushed-in vgroup. An Arrow with
non-tip members runs Community's literal put_start_and_end_on (Arrow.scale, rotate, shift).
When a tipped receiver with points becomes a pointless vgroup, become fills the pushed slot
with a childless copy of the receiver's class (Community's push_self_into_submobjects), so
later Arrow.scale calls on it return early as in Community. `_aligned_target` aligns a curved
receiver's pushed copy by its frozen drawn shaft points (flag dropped), not the refit path.
A NumberLine whose shaft child is gone (transformed into a shape) answers scene point queries
and edits (`_shaft_edit`, pointwise_become_partial) with its own points (`_has_shaft`).
TransformFromCopy.finish becomes `source._aligned_target(target)` when alignment changes the
target's family or point counts (Community ends at interpolate(0), the aligned start copy).
A pushed-in VGroup carries the pushed shape's root style (scene become copies it), but
Transform completion keeps a pointless receiver root's own style: Community interpolates only
members with points. `.animate` builders are exempt (_MethodAnimation.finish reapplies methods).
