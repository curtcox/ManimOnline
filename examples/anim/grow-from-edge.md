# `anim/grow-from-edge`

Introduce by growing from a bounding edge.

Docs: [growing](https://docs.manim.community/en/stable/reference/manim.animation.growing.html)

```py
from manim import *

class AnimGrowFromEdgeExample(Scene):
    def construct(self):
        shape = Square()
        self.play(GrowFromEdge(shape))
```
