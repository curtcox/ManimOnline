# `anim/transform-from-copy`

Transform a copy into a target.

Docs: [transform module](https://docs.manim.community/en/stable/reference/manim.animation.transform.html)

```py
from manim import *

class AnimTransformFromCopyExample(Scene):
    def construct(self):
        left = Square().shift(LEFT)
        right = Circle().shift(RIGHT)
        self.play(TransformFromCopy(left, right))
```
