# `anim/grow-from-center`

Introduce by growing from center point.

Docs: [growing](https://docs.manim.community/en/stable/reference/manim.animation.growing.html)

```py
from manim import *

class AnimGrowFromCenterExample(Scene):
    def construct(self):
        shape = Square()
        self.play(GrowFromCenter(shape))
```
