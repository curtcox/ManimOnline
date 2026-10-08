# `geometry/arrow`

Add arrowheads to directed lines.

Docs: [geometry](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.html)

```py
from manim import *

class GeometryArrowExample(Scene):
    def construct(self):
        shape = Arrow(LEFT, RIGHT)
        self.add(shape)
```
