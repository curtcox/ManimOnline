# `group/grid`

Arrange objects in a grid layout.

Docs: [VGroup](https://docs.manim.community/en/stable/reference/manim.mobject.types.vectorized_mobject.VGroup.html)

```py
from manim import *

class GridExample(Scene):
    def construct(self):
        dots = VGroup(*[Dot() for _ in range(9)]).arrange_in_grid(rows=3, cols=3, buff=0.4)
        self.add(dots)
```
