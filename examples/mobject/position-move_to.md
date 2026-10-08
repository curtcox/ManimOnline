# `mobject/position-move_to`

Place a mobject by moving its center.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class MoveToExample(Scene):
    def construct(self):
        dot = Dot().move_to(LEFT * 2)
        self.add(dot)
```
