# `geometry/boolean-exclusion`

XOR regions between shapes.

Docs: [boolean_ops](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.boolean_ops.html)

```py
from manim import *

class GeometryBooleanExclusionExample(Scene):
    def construct(self):
        left = Circle().shift(LEFT * 0.5)
        right = Circle().shift(RIGHT * 0.5)
        combined = Exclusion(left, right)
        self.add(combined)
```
