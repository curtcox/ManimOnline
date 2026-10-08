# `anim/create`

Draw a vectorized mobject incrementally.

Docs: [creation](https://docs.manim.community/en/stable/reference/manim.animation.creation.html)

```py
from manim import *

class AnimCreateExample(Scene):
    def construct(self):
        shape = Square()
        self.play(Create(shape))
```
