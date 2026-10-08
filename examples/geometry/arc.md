# `geometry/arc`

Draw arcs with defined angle and radius.

Docs: [geometry](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.html)

```py
from manim import *

class GeometryArcExample(Scene):
    def construct(self):
        shape = Arc(angle=PI / 2)
        self.add(shape)
```
