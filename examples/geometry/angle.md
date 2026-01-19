# `geometry/angle`

Visualize angles between two lines.

Docs: [geometry](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.html)

```py
from manim import *

class GeometryAngleExample(Scene):
    def construct(self):
        line1 = Line(LEFT, ORIGIN)
        line2 = Line(ORIGIN, UP)
        angle = Angle(line1, line2)
        self.add(line1, line2, angle)
```
