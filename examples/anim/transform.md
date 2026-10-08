# `anim/transform`

Morph one mobject into another.

Docs: [Transform](https://docs.manim.community/en/stable/reference/manim.animation.transform.Transform.html)

```py
from manim import *

class AnimTransformExample(Scene):
    def construct(self):
        square = Square()
        circle = Circle()
        self.play(Transform(square, circle))
```
