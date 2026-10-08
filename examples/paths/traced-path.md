# `paths/traced-path`

Draw the trajectory of a moving point.

Docs: [TracedPath](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.traced_path.TracedPath.html)

```py
from manim import *

class TracedPathExample(Scene):
    def construct(self):
        dot = Dot()
        path = TracedPath(dot.get_center, stroke_color=YELLOW)
        self.add(dot, path)
        self.play(dot.animate.shift(RIGHT * 3))
```
