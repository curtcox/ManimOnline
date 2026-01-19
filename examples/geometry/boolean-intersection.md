# `geometry/boolean-intersection`

Keep only overlapping regions of shapes.

Docs: [Intersection](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.boolean_ops.Intersection.html)

```py
from manim import *

class GeometryBooleanIntersectionExample(Scene):
    def construct(self):
        left = Circle().shift(LEFT * 0.5)
        right = Circle().shift(RIGHT * 0.5)
        combined = Intersection(left, right)
        self.add(combined)
```
