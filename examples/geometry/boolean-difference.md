# `geometry/boolean-difference`

Subtract one shape from another.

Docs: [Difference](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.boolean_ops.Difference.html)

```py
from manim import *

class GeometryBooleanDifferenceExample(Scene):
    def construct(self):
        left = Circle().shift(LEFT * 0.5)
        right = Circle().shift(RIGHT * 0.5)
        combined = Difference(left, right)
        self.add(combined)
```
