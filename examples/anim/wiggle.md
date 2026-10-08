# `anim/wiggle`

Wiggle a mobject briefly.

Docs: [indication](https://docs.manim.community/en/stable/reference/manim.animation.indication.html)

```py
from manim import *

class AnimWiggleExample(Scene):
    def construct(self):
        shape = Square()
        self.play(Wiggle(shape))
```
