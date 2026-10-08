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
6. `docs/rendering.md` for current gaps and next milestones.
7. `examples/multiple_scenes.py` for selection and geometry transform checks.
8. `examples/creation_and_rotation.py` for stroke creation and orbital motion.
9. `examples/layout_scene.py` for relative positioning and animated arrangements.
10. `examples/staggered_scene.py` for overlapping animation timing and cleanup.
11. `examples/path_scene.py` for transformed paths and center-following motion.
12. `examples/arc_scene.py` for open circular paths and signed sweeps.
13. `todo/master_plan.md` and the other `todo/` documents for background plans.

`ace/`, `viz-global.js`, and `svg-pan-zoom.min.js` are vendored dependencies.
Avoid editing these to implement Manim features. The Markdown files under
`examples/` illustrate the broader Manim API; they do not imply browser support.

## Implementation guidance

- Keep the edit → render → preview loop central. Preserve DOT rendering, sharing,
  and exports when changing the unified flow.
- Extend the existing static architecture before introducing another stack.
  Full Manim, video encoding, LaTeX, and offline support are not proven here.
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
