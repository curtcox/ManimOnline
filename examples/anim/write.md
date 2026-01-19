# `anim/write`

Handwrite text or draw a path.

Docs: [creation](https://docs.manim.community/en/stable/reference/manim.animation.creation.html)

```py
from manim import *

class AnimWriteExample(Scene):
    def construct(self):
        shape = Square()
        self.play(Write(shape))
```
