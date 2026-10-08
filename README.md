# [ManimOnline](https://curtcox.github.io/ManimOnline)

A web-based editor that supports both Graphviz DOT language diagrams and Manim Python animations, with automatic detection and appropriate rendering.

## Features

- **Graphviz DOT Support**: Full support for Graphviz DOT language diagrams
- **Manim-lite animations**: In-browser Python execution with SVG frame playback, play/pause, replay, and seeking
- **Auto-Detection**: Automatically detects whether input is DOT or Manim Python
- **URL Sharing**: Share diagrams via URL parameters
- **Export**: Download diagrams as SVG or PNG

## Usage

Visit the deployed site and start typing:
- For Graphviz: Write DOT language code (e.g., `digraph { a -> b }`)
- For Manim: Write a `Scene` subclass with `from manim import *` (see the supported subset below).

## Development

This is a static site that can be served directly. To run locally:

```bash
# Using Python
python -m http.server 8000

# Using Node.js
npx serve .
```

Then open `http://localhost:8000` in your browser.

## Agent orientation

- [AGENTS.md](AGENTS.md): project map and working guidance.
- [Rendering roadmap](docs/rendering.md): current limitations and next milestones.
- [Minimal scene](examples/minimal_scene.py): baseline animation input.

## Supported browser animation subset

Python runs in a Web Worker using Pyodide 0.27.0. The browser loads Python on
first use, so the first render needs an internet connection. This is a small
Manim-like runtime, **not the full Manim Community engine**.

- Shapes: `Circle`, `Square`, `Rectangle`, `Line`, `Arrow`, `Triangle`, `Polygon`,
  `Text`, and `VGroup`.
- Scene operations: `add`, `remove`, `play`, and `wait`.
- Animations: `Create`, `Write`, `FadeIn`, `FadeOut`, `Transform`, and
  `ReplacementTransform`; chained `.animate.shift()`, `.move_to()`,
  `.set_color()`, `.set_fill()`, and `.set_stroke()`.
- Timing: `run_time`, `linear`/`smooth` rate functions, and simultaneous animations.
- Directions support vector addition/subtraction and scalar multiplication,
  such as `RIGHT * 2`.

`Create` and `Write` currently reveal objects by fading them in. Transforms
interpolate matching geometry and crossfade between different shape types.
The first scene defined in the source is rendered. Animation previews run at
15 frames per second and are limited to 60 seconds, with a 90-second deadline
for loading and execution. Editing cancels active computation. Download saves
the current SVG frame, not a video.

LaTeX/`MathTex`, 3D, updaters, full NumPy integration, MP4 export, and offline
caching are not implemented. The broader examples directory includes APIs
outside this subset. Unsupported operations report Python errors.

## Verification

No dependency installation is needed for the tests:

```sh
python3 -m unittest discover -s tests -v
node --test tests/*.test.js
```

Serve the site locally to check actual Pyodide loading and browser playback.
Check the default animation, replay/seek, a source edit, invalid Python, and
switching to `digraph { a -> b }`. These unit tests cover the compatibility
runtime and worker lifecycle; they do not substitute for browser checks.

## Credits

- Based on [GraphvizOnline](https://github.com/dreampuf/GraphvizOnline) by Dreampuf (BSD-3-Clause)
- Uses [viz.js](https://github.com/mdaines/viz.js) for Graphviz rendering
- Uses [Pyodide](https://pyodide.org/) for browser Python execution
- Uses [ACE Editor](https://ace.c9.io/) for code editing
- Uses [svg-pan-zoom](https://github.com/ariutta/svg-pan-zoom) for SVG interaction

## License

BSD-3-Clause (see LICENSE-graphvizonline for GraphvizOnline attribution)
