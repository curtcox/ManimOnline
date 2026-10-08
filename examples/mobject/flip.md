# `mobject/flip`

Mirror across an axis.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class FlipExample(Scene):
    def construct(self):
        arrow = Arrow(LEFT, RIGHT).flip(UP)
        self.add(arrow)
```
