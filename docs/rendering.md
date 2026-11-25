# Rendering support and limitations

ManimOnline runs Manim scenes in the browser with **Manim-lite**, a single-file Python
compatibility layer (`src/manim-lite.py`) that follows Manim Community 0.22. It is
checked against Community, but it is not the Community engine: it produces vector
frames for an SVG player rather than Cairo or OpenGL pixels. Graphviz DOT and modl
diagrams use their own renderers and are unaffected by Manim-lite.

## Pipeline

1. **Detect and schedule.** `src/detector.js` scores the source with strings and comments
   removed; the Renderer selector can override it. The Fragment Kit scheduler coalesces
   edits (detection after 300 ms, rendering after one second) and drops stale callbacks.
2. **Execute.** `src/manim-client.js` runs one render at a time with a 90-second deadline,
   terminating the worker on timeout, Cancel or a newer edit. `src/manim-sandbox.js`
   starts `src/unified-worker.js` as a classic worker inside the HashBin SDK's
   opaque-origin sandbox iframe, so scene code never runs with the app's origin. The
   worker loads Pyodide 0.27.0, `manim-lite.py` and `text-outlines.json` from the verified
   cache, executes the source in a fresh namespace, and loads NumPy, Pillow, Pygments or
   networkx only when the source needs them.
3. **Capture.** `Scene.render` runs `setup`, `construct` and `tear_down`, sampling every
   `play`/`wait` at 15 fps into serialized frames. Frames are pooled (`compact=True`):
   repeated snapshots and arrays are shared, and 3D solids that move rigidly reuse
   earlier geometry with a per-frame transform.
4. **Measure formulas.** `src/manim-math.js` typesets `MathTex`/`Tex` with MathJax 3.2.2
   and `src/manim-typst.js` compiles `Typst`/`MathTypst` with typst.ts (both loaded on
   first use). Their measured sizes, glyph boxes and outlines are fed back into a second
   render pass so layout uses real dimensions.
5. **Draw and play.** `src/manim-renderer.js` turns each frame into SVG (projecting,
   shading and depth-sorting `ThreeDScene` frames) and `src/manim-player.js` handles
   play/pause, replay and seeking.
6. **Export.** `src/manim-export.js` saves the current frame as SVG or PNG;
   `src/manim-video.js` encodes every frame with WebCodecs and muxes MP4 (H.264) or WebM
   (VP9/VP8) in memory, timed by frame index.

## Limits

| Limit | Value |
| --- | --- |
| Frame rate | 15 fps (`config.frame_rate` is accepted and ignored) |
| Duration | 120 seconds (1,800 sampled frames plus the final state) |
| Execution deadline | 90 seconds per render |
| Serialized result | 32 MiB |
| Default canvas | 800 × 450 pixels, frame height 8 units |

The deadline stops Python but not synchronous MathJax typesetting, and Python memory
use is not bounded. `config` quality, resolution and output flags are stored but only
the pixel dimensions, frame size, background and seed affect the preview.

## Supported API

The scene namespace exports about 250 Community classes plus constants, colors and
utility functions. In outline:

- **Scenes and cameras:** `Scene`, `MovingCameraScene` (pan, zoom, auto framing),
  `ZoomedScene` (vector inset views), `ThreeDScene`/`SpecialThreeDScene` with
  `ThreeDCamera` motion, `VectorScene`, `LinearTransformationScene`; sections,
  `skip_animations`, scene updaters, `wait_until`, `bring_to_front`/`back`, foreground
  mobjects, `clear`, and Community's manual frame loop.
- **Geometry:** arcs, circles, ellipses, sectors, annuli, polygons, polygrams, stars,
  rounded rectangles, lines, dashed lines and paths, tangent lines, angles, elbows,
  arrows (all tip shapes, double and curved arrows), braces, cubic Béziers, raw
  `VMobject` paths with multiple contours, boolean operations (`Union`, `Intersection`,
  `Difference`, `Exclusion`), `Cutout`, convex hulls and shape matchers
  (`SurroundingRectangle`, `BackgroundRectangle`, `Cross`, `Underline`).
- **Groups and layout:** `Group`, `VGroup`, `VDict`, indexing/slicing, `next_to`,
  `arrange`, `arrange_in_grid`, alignment and frame-edge placement, `stretch`,
  `apply_matrix`/`apply_function`/`apply_complex_function`, `z_index` depth ordering.
- **Text:** `Text`, `MarkupText`, `Paragraph`, `Code`, `DecimalNumber`/`Integer`,
  `Variable`, `Title`, `BulletedList`, `Table` family, `Matrix` family.
- **Formulas:** `MathTex`, `Tex`, `SingleStringMathTex` with `{{ }}` parts, isolated
  substrings, `tex_to_color_map` and glyph indexing; `Typst` and `MathTypst`.
- **Coordinates and plots:** `NumberLine` (linear and log scales), `Axes`, `ThreeDAxes`,
  `NumberPlane`, `ComplexPlane`, `PolarPlane`, `BarChart`, `ParametricFunction`,
  `FunctionGraph`, `ImplicitFunction`, graph areas, Riemann rectangles, secants,
  derivatives and integrals, `plot_surface`.
- **3D:** `Surface`, `Sphere`, `Cube`, `Prism`, `Cone`, `Cylinder`, `Torus`, `Line3D`,
  `Arrow3D`, `Dot3D`, the Platonic polyhedra and `ConvexHull3D`, with shading and
  depth sorting.
- **Fields and graphs:** `ArrowVectorField`, `StreamLines` (2D and spatial), raster
  `VectorField` images, `Graph`/`DiGraph` with networkx-exact layouts.
- **Media:** `SVGMobject`, `VMobjectFromSVGPath`, `ImageMobject` (arrays, Pillow images,
  data URIs, files written to Pyodide's file system), point clouds.
- **Animations:** creation (`Create`, `Write`, `DrawBorderThenFill`, letter/word text
  animations, typing cursors), fades and growth, every `Transform` variant including
  `TransformMatchingShapes`/`Tex`, `FadeTransform` and path arcs, `.animate` builders,
  movement and rotation, pointwise and functional animations (`Homotopy`, `ApplyWave`,
  `PhaseFlow`), indication (`Indicate`, `Flash`, `Circumscribe`, `Wiggle`,
  `ShowPassingFlash`), composition (`AnimationGroup`, `LaggedStart`, `LaggedStartMap`,
  `Succession`, `ChangeSpeed`), `UpdateFromFunc`, and custom `Animation` subclasses,
  including the manual `begin`/`interpolate`/`finish` protocol.
- **State and updaters:** `ValueTracker`, `ComplexValueTracker`, `always_redraw`,
  `add_updater`, `TracedPath`, `save_state`/`restore`, `become`, `generate_target`.
- **Style:** `ManimColor` with Community's palette and operators, fill/stroke/background
  stroke channels, gradients and sheen, `match_style`, `interpolate_color`, raster
  background paint.
- **Utilities:** NumPy-compatible points (`points` is a writable array when NumPy is
  loaded), Community's space-ops, Bézier, rate-function, path and iterable utilities,
  `manim.utils.unit`, `manim.typing` and submodule imports such as
  `from manim.mobject.geometry.arc import Circle`.

Scene code sees members of posed families (arrow tips, children of rotated axes or
shapes) in world coordinates, as in Community.

## Text and formulas

- `Text`, `MarkupText`, `Paragraph` and `Code` draw Community's exact glyph outlines for
  Liberation Sans (sans text) and DejaVu Sans Mono (monospace), reproducing manimpango's
  layout, Pango markup and Cairo's glyph paths. Other fonts use metric layout and browser
  text. Pango's `low` and `error` underline styles are drawn as single underlines.
- `DecimalNumber` and `Integer` use Computer Modern outlines with Community's layout.
- `MathTex` and `Tex` outlines come from MathJax's TeX fonts, so they are close to, but
  not identical to, Community's Computer Modern paths. Formulas are estimated until the
  browser measures them. Custom LaTeX packages, preambles and full LaTeX documents are
  not available; `TexTemplate` objects are accepted and ignored.
- First formula use needs a connection unless the runtime is already cached.

## How fidelity is checked

- `tests/test_manim_lite.py` and `tests/test_community_api.py` (native Python) cover
  geometry, timing, frame state and Community-measured values;
  `tests/fixtures/community_reference.json` holds Manim 0.22 bounds for reference snippets.
- JavaScript tests cover the renderer, 3D projection, player, math, Typst, export, video
  muxing, worker decoding and the client deadline.
- Browser suites (`tests/browser/`) render DOT, modl and Manim scenes in Chromium, Firefox
  and WebKit, including pixel checks on exported frames.
- Differential runs against a Manim Community 0.22 install compare per-frame bounds,
  structure and durations across Community's docstring examples, its own module tests,
  this gallery and randomly generated scenes. Results are summarized in
  [completion](completion.md).

## Known gaps

- **Renderers and cameras:** no OpenGL renderer and no pixel output. OpenGL point-cloud
  classes and pixel cameras (`MappingCamera`, `SplitScreenCamera`, `OldMultiCamera`) are
  importable but raise `NotImplementedError`, as do `get_image`, `get_pixel_array` and
  `show`.
- **Paint:** exact Cairo antialiasing and raster arithmetic, stored-RGBA and sheen
  regeneration edge cases, gradient bounds sampled during animations, 3D glyph
  gradients, and percentage lengths in MathJax delimiter viewports.
- **SVG input:** gradients, patterns and clip paths are not imported; `url()` paints are
  black.
- **Other:** custom Pygments `Style` classes, SciPy-based graph layouts, exact boolean
  results on coincident curved boundaries, pixel interpolation of images in `Transform`,
  arranging or inverting zero-scale groups, audio and subcaptions (recorded, not played),
  and Python packages other than NumPy, Pillow, Pygments and networkx.

Report a scene that runs in Community 0.22 but fails or differs here as a compatibility
bug.

## Beyond this architecture

The site is static and executes Python only in the browser. Full Manim Community in
WebAssembly has not been demonstrated. If a server is ever introduced, submitted Python
needs runtime isolation, resource limits, disabled host and network access, and per-job
artifact storage; never execute user scenes in a web server process.

## References

- [Manim Community documentation](https://docs.manim.community/en/stable/)
- [Pyodide in a web worker](https://pyodide.org/en/stable/usage/webworker.html)
- [MathJax SVG output](https://docs.mathjax.org/en/v3.2/options/output/svg.html)
- [typst.ts](https://github.com/Myriad-Dreamin/typst.ts)
