# Agent orientation

## Goal and current state

Build a browser experience for editing Manim scene source, requesting a render,
and playing the resulting animation. The original project idea is
“GraphvizOnline but Manim.” Keep the edit → render → preview loop central.

The repository currently contains documentation and an example scene only.
There is no application, renderer, package manifest, CI, or test suite.
Do not infer an existing stack or report the project as runnable.

## Read first

1. `README.md` for the public project overview.
2. `docs/rendering.md` for the proposed milestone, open decisions, and verification.
3. `examples/minimal_scene.py` for a small rendering input.

## Implementation guidance

- Treat the roadmap as a proposal, not an already approved architecture.
  Browser access does not require that Manim itself execute inside the browser.
- Investigate the rendering runtime before building a large editor UI. Prove
  that the example can produce a video the target browser can play.
- Prefer a small end-to-end slice: source input, explicit scene selection,
  render status, useful errors, and video playback/download.
- Use Manim Community as the initial investigation target; record the chosen
  version and renderer when introducing dependencies. Other Manim variants are
  not assumed compatible.
- User scene source is executable Python. For a server design, isolate rendering
  from the web process and host, with resource limits and per-job storage.
  A subprocess alone is not a sandbox. See the roadmap for the required boundaries.
- Keep generated videos, caches, and job directories out of version control.
  Add scoped ignore rules when introducing tools that generate them.
- Avoid speculative infrastructure, accounts, sharing features, and dependency
  installs for documentation-only tasks.

## Verification and handoff

There are no repository test commands yet. Do not invent them or claim a real
render from syntax checks or mocks. Once code exists, document exact setup and
verification commands in the README and update these notes to reflect reality.

For rendering changes, verify successful playback, actionable scene errors,
timeout/cancellation behavior, and isolation between jobs as appropriate to the
change. Report what was actually run and any remaining environment limitations.
