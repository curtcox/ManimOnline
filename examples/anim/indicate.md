# `anim/indicate`

Temporarily resize/recolor to draw attention.

Docs: [indication](https://docs.manim.community/en/stable/reference/manim.animation.indication.html)

```py
from manim import *

class AnimIndicateExample(Scene):
    def construct(self):
        shape = Square()
        self.play(Indicate(shape))
```
