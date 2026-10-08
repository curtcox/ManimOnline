# `mobject/stretch`

Stretch a mobject along a single axis.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class StretchExample(Scene):
    def construct(self):
        rect = Square().stretch(2, dim=0)
        self.add(rect)
```
