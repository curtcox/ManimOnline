# `anim/draw-border-then-fill`

Draw outline first, then reveal fill.

Docs: [creation](https://docs.manim.community/en/stable/reference/manim.animation.creation.html)

```py
from manim import *

class AnimDrawBorderThenFillExample(Scene):
    def construct(self):
        shape = Square()
        self.play(DrawBorderThenFill(shape))
```
