# `mobject/rotate`

Rotate around a point and axis.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class RotateExample(Scene):
    def construct(self):
        triangle = Triangle().rotate(PI / 4)
        self.add(triangle)
```
