# Browser rendering direction

## Current architecture

ManimOnline is a static editor deployed through `.github/workflows/deploy.yml`.
`index.html` integrates ACE, DOT detection, Graphviz rendering, and a Pyodide
Manim-lite path. `src/manim-renderer.js` turns serialized shapes into SVG;
`src/unified-worker.js` contains an early worker implementation. The imported
implementation currently has duplicated Python definitions, main-thread Python
execution, and no-op `play()`/`wait()` methods. Animation support is incomplete.

The established direction in `todo/master_plan.md` is in-browser execution and
frame playback. Full native Manim in WebAssembly has not been demonstrated.
Manim-lite is a compatibility subset, not the Manim Community engine.

## Next milestone

1. Consolidate the Python compatibility layer into one source.
2. Execute scenes in a worker, with a hard timeout enforced by the main thread.
3. Use a fresh namespace for each render and prevent stale results after edits.
4. Implement basic timed creation, fades, transforms, and waits.
5. Provide play/pause, replay, and seeking for the generated SVG frames.
6. Keep DOT rendering and static SVG download working.

Use `examples/minimal_scene.py` as a baseline. Broader examples under `examples/`
are feature references, not an acceptance claim. Document unsupported APIs and
limits on duration/frame count. MP4 export, LaTeX, 3D, arbitrary dependencies,
updaters, and offline caching remain future work unless separately implemented.

## Verification

Check initial Pyodide loading, a visible animation, seeking/replay, source edits,
syntax errors, missing scenes, and a runaway loop timeout. Ensure a new source
cannot select a scene class left behind by an older render. Check DOT rendering
and export after switching away from Manim. Run tests for timing and frame state
independently of browser integration; report both categories separately.

## References

- [Manim quickstart](https://docs.manim.community/en/stable/tutorials/quickstart.html)
- [Manim configuration](https://docs.manim.community/en/stable/guides/configuration.html)
- [Pyodide worker guidance](https://pyodide.org/en/stable/usage/webworker.html)

If full Manim Community rendering becomes a requirement, revisit runtime
feasibility. A server design must isolate arbitrary submitted Python, enforce
resource limits, disable unwanted host/network access, and clean up per-job
artifacts. Do not execute user scenes in a web server process.
