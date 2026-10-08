# `anim/homotopy`

Warp points via a time-dependent mapping.

Docs: [movement](https://docs.manim.community/en/stable/reference/manim.animation.movement.html)

```py
from manim import *

class AnimHomotopyExample(Scene):
    def construct(self):
        square = Square()
        def homotopy(x, y, z, t):
            return np.array([x + 0.5 * np.sin(t + y), y, z])
        self.play(Homotopy(homotopy, square))
```
