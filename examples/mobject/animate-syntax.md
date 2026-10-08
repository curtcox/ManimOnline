# `mobject/animate-syntax`

Use `.animate` to create implicit animations.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class AnimateSyntaxExample(Scene):
    def construct(self):
        square = Square()
        self.add(square)
        self.play(square.animate.shift(UP))
```
