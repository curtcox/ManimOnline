# `geometry/boolean-union`

Combine shapes using vector-graphics union.

Docs: [boolean_ops](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.boolean_ops.html)

```py
from manim import *

class GeometryBooleanUnionExample(Scene):
    def construct(self):
        left = Circle().shift(LEFT * 0.5)
        right = Circle().shift(RIGHT * 0.5)
        combined = Union(left, right)
        self.add(combined)
```
