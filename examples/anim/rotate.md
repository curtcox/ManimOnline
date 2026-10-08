# `anim/rotate`

Animate rotation with angle and axis.

Docs: [Rotate](https://docs.manim.community/en/stable/reference/manim.animation.rotation.Rotate.html)

```py
from manim import *

class AnimRotateExample(Scene):
    def construct(self):
        arrow = Arrow(LEFT, RIGHT)
        self.play(Rotate(arrow, angle=PI / 2))
```
