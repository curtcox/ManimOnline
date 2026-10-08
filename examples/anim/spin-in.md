# `anim/spin-in`

Spin and grow from nothing.

Docs: [growing](https://docs.manim.community/en/stable/reference/manim.animation.growing.html)

```py
from manim import *

class AnimSpinInExample(Scene):
    def construct(self):
        shape = Square()
        self.play(SpinInFromNothing(shape))
```
