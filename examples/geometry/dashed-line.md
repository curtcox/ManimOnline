# `geometry/dashed-line`

Use dashed strokes for emphasis or guides.

Docs: [geometry](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.html)

```py
from manim import *

class GeometryDashedLineExample(Scene):
    def construct(self):
        shape = DashedLine(LEFT, RIGHT)
        self.add(shape)
```
