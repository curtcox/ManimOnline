# Browser-based Manim rendering roadmap

## Intent and known facts

The user-facing goal is a short loop: edit Python scene source in a browser,
choose a scene, render it, then play or download the animation. The repository
has no implementation yet; all architecture below is proposed.

Manim Community scenes normally subclass `Scene` and implement `construct()`.
Its CLI accepts a source file and scene names. See the official
[quickstart](https://docs.manim.community/en/stable/tutorials/quickstart.html)
and [configuration reference](https://docs.manim.community/en/stable/guides/configuration.html).

## First investigation: where rendering runs

Evaluate these paths before committing to a stack:

| Path | What to prove | Main tradeoff |
| --- | --- | --- |
| Browser UI with an isolated server worker | A pinned Manim environment produces browser-playable video and can safely execute submitted scenes | Requires server compute, job limits, and cleanup |
| Entirely in-browser runtime | Python, Manim's native dependencies, and video encoding work in the target browsers | Requires a compatibility proof; feasibility is unverified |

A server worker is the proposed starting path because it can use a conventional
Manim environment. This is a recommendation, not a recorded project decision.
If an entirely local browser runtime is a requirement, investigate that path
before building around a server API.

For either path, record the Manim version, Python version, renderer, dependency
setup, output format, and target browser. Use the minimal example to prove
rendering and playback. Begin with basic shapes; introduce text and LaTeX after
the baseline works. LaTeX is optional for scenes that do not need it; see
[Manim's installation guide](https://docs.manim.community/en/stable/installation/conda.html).
Consult the installation instructions for the selected version rather than
assuming dependencies from older tutorials.

## Proposed first end-to-end milestone

1. Load a working example into an editable source field.
2. Accept an explicit scene class name and a fixed low-quality preview preset.
3. Submit a render and show queued/running/succeeded/failed status.
4. Play a completed video with browser controls and offer a download.
5. Show bounded, useful diagnostics when a scene fails; preserve the source.
6. Allow another edit and render without mixing results from different jobs.

Keep authentication, public sharing, collaboration, and a gallery outside this
first milestone unless a later request adds them.

## Proposed boundaries for a server implementation

```text
Browser editor → render API → isolated render worker → job artifact storage
       ↑              │                                  │
       └── status/error response and playable artifact ──┘
```

The browser owns source editing and playback. The API validates request size,
scene name, and allowed rendering settings, then manages job status. A worker
runs Manim in a separate, restricted job environment. Artifact storage exposes
only the intended completed output, never arbitrary worker file paths.

- Treat every scene as arbitrary Python execution, including at import time.
  Scene discovery must also occur in isolation if it imports source.
- Give each job its own working directory and output namespace. Do not allow
  user-controlled paths, shell commands, or arbitrary CLI flags.
- Invoke tools with argument arrays; do not interpolate scene source into a
  shell command. Input validation does not replace runtime isolation.
- Enforce wall-clock, CPU, memory, process, disk, output-size, and concurrency
  limits. Limit logs as well as video artifacts.
- Keep secrets and host mounts out of the job environment; restrict network
  access. A plain subprocess or default container is not sufficient evidence
  of isolation for publicly submitted code.
- Define cancellation/timeout handling that stops the job's child processes,
  records a terminal status, and removes temporary files.
- Define artifact retention and cleanup. Return opaque job/artifact identifiers
  and avoid serving partial output as a successful render.

Do not execute submitted scenes directly in the API process. Establish these
boundaries before exposing a service to untrusted users.

## Acceptance checks once an implementation exists

| Check | Expected result |
| --- | --- |
| Minimal example | Produces a nonempty video that visibly animates a circle into a square and plays in the target browser |
| Edit and rerender | The preview corresponds to the new source; stale job results do not replace it |
| Syntax error or missing scene | Clear failure diagnostics; editing remains usable |
| Slow or looping scene | Job stops at the configured timeout and reaches a terminal status |
| Cancellation, if supported | Work stops and the UI reports cancellation |
| Two independent jobs | Outputs, logs, and temporary files remain separate |
| Completed/failed job cleanup | Files expire according to the documented retention policy |

For a server path, also verify the configured resource and access restrictions
using controlled checks before public exposure. Mocked API responses can test
the UI but do not prove rendering, playback, or worker isolation.

## Decisions to record during implementation

- Rendering location and why it meets the intended browser experience.
- Manim variant/version, Python runtime, renderer, and supported scene features.
- Browser targets and video format/codec verified for playback.
- Frontend/backend stack, job status transport, and deployment environment.
- Preview limits, concurrency policy, cancellation support, and retention.
- Whether uploads, extra dependencies, text/LaTeX, or higher-quality export are
  supported; do not imply these work before verifying them.

Update this document and the README as decisions become implemented behavior.
