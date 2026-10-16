# modl deep-zoom prototype

The existing SVG group camera can support **0.001×–1000×**, a 1,000,000:1 range
(six orders of magnitude), for ordinary modl layouts. Extending the two constants
alone is insufficient: integer dragging becomes unusable, deeply zoomed nodes
can cover the background used for panning, and scaled shadows make dragging slow.
This prototype addresses those problems without changing modl syntax or saves.
It is not an infinite canvas or an arbitrary-coordinate renderer.

## Implementation

- `src/modl.js` retains `screen = translation + scale × world`. Zoom computes the
  old world point under the cursor and chooses the new translation to preserve it,
  including at the scale clamps. This matches SVG's
  [translate/scale coordinate mapping](https://www.w3.org/TR/SVG2/coords.html).
- Root SVG screen-coordinate inversion handles CSS sizing/viewBox mapping. Wheel
  deltas use pixel, line and page units; an event's exponent is bounded to avoid
  extreme jumps. Horizontal-only events do not zoom. The existing 1.2× button
  step remains available through the prototype API and editor controls.
- Drag positions use the initial world position plus screen displacement divided
  by scale. No whole-unit rounding: a 23-pixel drag at 1000× moves 0.023 units.
  Three CSS pixels distinguish dragging from following a node link. Pointer
  cancellation/lost capture ends the gesture; another pointer cannot take it over.
  Camera changes are ignored during a drag/pan so its initial anchors stay valid.
- Left-drag the background to pan; middle-drag anywhere to pan over a giant node.
  **Reset view** restores scale 1 and translation zero. The zoom readout and
  centered **−/+** controls are outside the exported SVG.
- At scales below 0.1× or above 8×, a scoped SVG style suppresses decorative
  filters. All shape, text, image, edge, marker and hit-target geometry remains.
  Returning to ordinary scales restores shadows. The style is serialized with the
  SVG, so export retains the current appearance without pruning geometry.
- ManimOnline serializes the SVG for the initial download link and refreshes it
  on download, auxiliary click or context-menu access. Pan/zoom callbacks update
  the scale display without serializing the whole tree. Export remains the
  current 800 × 450 viewport, with offscreen geometry retained in the document.
- Camera state remains separate from `pos`. Fractional positions survive existing
  URL/HashBin formats; moving the camera does not change source or saved layout.
  Re-rendering edited source resets the camera. Offline cache version is v372.

`Modl.create` also exposes `viewport()` (a copy), `zoom(factor, x=400, y=225)` and
`resetView()`. The optional `onFrame(svg, viewport)` callback receives a camera
copy. Parsing, quoted vocabulary, image sizing, DOT and Manim pipelines retain
their existing architecture.

## Numerical findings

The deterministic unit stress test performs 20,000 zoom operations interleaved
with pans and scale changes across the range. Maximum double-precision anchor
error was approximately **1.8e-7 screen units**; the regression bound is 1e-6.
The browser test's native SVG matrix anchor error was approximately **1.44e-5
pixels** in Chromium and WebKit near ordinary coordinates. Real pointer drags
at 1×, 100× and 1000× moved the node within 0.1 screen pixel of the request.

Large absolute coordinates are a separate problem. The diagnostic places a node
at the indicated X origin and directly installs a mathematically centered 1000×
transform, isolating native SVG geometry/transform behavior from pointer events.
These are bounding-rectangle diagnostics, not screenshots of distant geometry:

| X origin | Chromium center error, px | WebKit center error, px |
| ---: | ---: | ---: |
| 400 | 0 | 0 |
| 1,000,000 | 966,445,168 | 16 |
| 1,000,000,000 | 33,520,927,344 | 3,696 |
| 1,000,000,000,000 | 33,520,927,344 | 8,912,496 |

Chromium also clamps sufficiently large local geometry bounds (the 1e9 and 1e12
nodes reported local centers near 33,554,483). WebKit's local bounds at 1e12
already round to 999,999,995,904. Passing finite JavaScript values or changing to
a large `viewBox` does not establish reliable native rendering.

**Rebasing is required before promising deep zoom around very distant origins.**
A future camera should store a world origin and emit `world − origin` geometry
near zero, then translate only by a small screen offset. Merely nesting another
large negative translation leaves the large coordinates in the SVG pipeline.
Keep saved world positions unchanged, convert pointer edits back through the
origin, and rebase edge endpoints, images and export consistently. At still
larger magnitudes the source doubles themselves lose small increments; rebasing
cannot recover information already lost in stored positions. This work is not
implemented in the minimal prototype.

## Rendering measurements

Measured locally on macOS with headless Playwright Chromium, 800 × 450 SVG,
100/1,000/5,000 square nodes with labels and connecting labeled dashed edges.
Each camera sample includes a browser frame boundary; 24 samples per scale and
mode, 12 synthetic drag updates at 1000×. Values are illustrative, not a portable
frame-rate guarantee. The drag benchmark exercises the actual pointer handlers
and full SVG rebuild, while the regression suite also uses real mouse input.

| Nodes | SVG elements | Initial build, ms | Zoom median at .001× / 1× / 1000×, ms | Drag median at 1000×, ms |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 925 | 2.6 | 16.9 / 16.8 / 16.9 | 18.8 |
| 1,000 | 9,025 | 24.3 | 16.9 / 17.3 / 17.3 | 21.0 |
| 5,000 | 45,025 | 81.0 | 65.1 / 81.9 / 66.8 | 74.8 |

Before suppressing extreme-scale shadows, drag medians were 101.7 / 92.4 / 91.4
ms respectively. The small filter detail policy materially improves high-zoom
dragging for smaller diagrams; full rebuild and paint costs dominate at 5,000.
At that size, serializing SVG on every camera change adds about 24–26 ms of
synchronous work (URI encoding would add more). The benchmark compares this
legacy callback cost against the deferred-export prototype using the same tree.

**Full culling/semantic LOD is unnecessary for the tested smaller layouts, but
needed for interactive performance on dense diagrams at this scale.** Future
work should first update only the dragged node and incident edges, then use
conservative viewport culling with margins for shadows, labels, markers and
crossing edges. Keep a full scene model and export all geometry independently of
any display-only culling. A spatial index avoids scanning every node each frame;
label suppression or aggregation helps a zoomed-out overview. These changes have
more complexity than the bounded prototype and are not implemented here.

## Standalone modl implementation and patch

The same implementation is applied directly to standalone modl in
[commit 52eac38](https://github.com/curtcox/modl/commit/52eac38), including its own
browser regression test and three-browser CI workflow. Both actual local editors
passed Chromium and WebKit checks, and their validated cursor-anchor arithmetic
is identical. The standalone test can also target the published editor.

The supplied [patch](../patches/modl-deep-zoom.patch) remains available for the
historical base `01693302579a478808fdb4252995d128582e4ff6`. It was verified with
`git apply --check` and tested as a patched temporary HTML copy before being
applied to the repository. Do not apply it again to an updated checkout.

Apply from the modl repository:

```sh
git apply --check /path/to/ManimOnline/patches/modl-deep-zoom.patch
git apply /path/to/ManimOnline/patches/modl-deep-zoom.patch
```

To verify an updated standalone checkout instead, serve it on port 8001 and run:

```sh
node scripts/build-docs.mjs --check
node tests/browser/deep-zoom.cjs http://localhost:8001/ chromium firefox webkit
```

The port retains its self-contained HTML structure, native responsive viewBox,
source persistence and panning cursor class. It adds the same bounds, arithmetic,
fractional dragging, pointer lifecycle, middle panning and filter detail policy,
plus wheel zoom and reset/readout controls. Centered buttons now use SVG viewBox
units, which also handles a CSS viewport smaller than its minimum viewBox.
The standalone editor has no existing SVG download control to preserve; its DOM
still serializes as SVG. ManimOnline's Download control is tested separately.

## Verification and remaining limits

```sh
python3 -m unittest discover -s tests -v
node --test tests/*.test.js
python3 -m http.server 8000
node tests/browser/modl-zoom.cjs http://localhost:8000/ chromium firefox webkit
node tests/browser/modl-zoom.cjs http://localhost:8000/ chromium --benchmark
node tests/browser/languages.cjs http://localhost:8000/ chromium webkit
MODL_STANDALONE_HTML=/path/to/patched/modl/index.html node tests/browser/modl-zoom.cjs http://localhost:8000/ chromium webkit
```

Local verification: **147 JavaScript tests passed**; bundled Python ran **749
tests successfully, with one Pygments skip**. System `python3` also ran all 749,
but lacked NumPy/Pillow and had six dependency errors and eleven skips; the bundled
environment supplied those dependencies. Chromium and WebKit passed deep-zoom,
fractional drag/persistence, background/middle pan, pointer cancellation, wheel
modes, CSS sizing, asynchronous image loads and rasterized SVG export checks.
Their three-language suites passed real DOT, modl and Pyodide/Manim rendering and
mocked HashBin round trips, including the new controls and current-camera download.
Firefox was attempted but could not launch locally ("Could not find profile
folder"); both repositories include three-browser CI workflows for that coverage.
Published test and deployment results are available in each repository's commit
checks.

Tiny nodes become subpixel and impractical to select at 0.001×. An additional
native-mouse probe could drag a precisely targeted normal node in Chromium, but
WebKit hit the background and panned instead, despite a programmatic hit test
finding the node. Minimum-scale dragging therefore has no cross-browser targeting
guarantee; use zoom-in or reset to edit these nodes. There is no pinch gesture, fit-to-content, spatial index,
semantic hierarchy or new node-size syntax. Browser/device performance varies;
remote images remain external SVG references with the existing network/CORS
limitations. Large coordinate origins, huge images and dense documents remain
outside the prototype's performance/precision guarantees.
