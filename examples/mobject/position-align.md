# `mobject/position-align`

Align edges/centers between mobjects.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class AlignExample(Scene):
    def construct(self):
        left = Square().shift(LEFT)
        right = Circle().shift(RIGHT)
        right.align_to(left, UP)
        self.add(left, right)
```
