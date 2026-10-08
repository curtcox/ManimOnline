# `anim/replacement-transform`

Replace old mobject while transforming to new.

Docs: [transform module](https://docs.manim.community/en/stable/reference/manim.animation.transform.html)

```py
from manim import *

class AnimReplacementTransformExample(Scene):
    def construct(self):
        left = Square().shift(LEFT)
        right = Circle().shift(RIGHT)
        self.play(ReplacementTransform(left, right))
```
