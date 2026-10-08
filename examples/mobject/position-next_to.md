# `mobject/position-next_to`

Position relative to another mobject.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class NextToExample(Scene):
    def construct(self):
        circle = Circle()
        square = Square().next_to(circle, RIGHT)
        self.add(circle, square)
```
