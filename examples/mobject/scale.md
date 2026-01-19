# `mobject/scale`

Scale a mobject uniformly or by dimension.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class ScaleExample(Scene):
    def construct(self):
        square = Square().scale(0.6)
        self.add(square)
```
