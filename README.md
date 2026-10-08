# ManimOnline

GraphvizOnline but Manim: write a Manim scene in a browser, render it, and watch
the resulting animation without installing Manim on the user's computer.

## Project status

This project is at the planning stage. There is no browser app, rendering
service, dependency manifest, or automated test suite yet. The implementation
language, framework, hosting platform, and rendering runtime are still open.

“Browser-based” describes the intended user experience. Whether rendering runs
in the browser or on a server has not been decided.

## Start here

- [AGENTS.md](AGENTS.md): orientation and working guidance for coding agents.
- [Rendering roadmap](docs/rendering.md): proposed first milestone, runtime
  investigation, boundaries, and acceptance checks.
- [Minimal example](examples/minimal_scene.py): a short scene for an initial
  rendering smoke check once a Manim runtime is available.

There is no project setup command yet. In an environment with Manim Community
installed, the example can be rendered from the repository root with:

```sh
manim -ql examples/minimal_scene.py MinimalScene
```

This is a standalone Manim command, not a working ManimOnline application.
See the official [Manim quickstart](https://docs.manim.community/en/stable/tutorials/quickstart.html)
for scene and rendering basics.
