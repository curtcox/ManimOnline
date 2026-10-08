# `anim/move-along-path`

Move an object along a curve path.

Docs: [movement](https://docs.manim.community/en/stable/reference/manim.animation.movement.html)

```py
from manim import *

class AnimMoveAlongPathExample(Scene):
    def construct(self):
        dot = Dot()
        path = Circle(radius=2)
        self.add(path)
        self.play(MoveAlongPath(dot, path))
```
