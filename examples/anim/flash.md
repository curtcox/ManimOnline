# `anim/flash`

Emit radial “flash” strokes from a point.

Docs: [indication](https://docs.manim.community/en/stable/reference/manim.animation.indication.html)

```py
from manim import *

class AnimFlashExample(Scene):
    def construct(self):
        shape = Square()
        self.play(Flash(shape))
```
