# `anim/succession`

Play animations in strict sequence.

Docs: [Succession](https://docs.manim.community/en/stable/reference/manim.animation.composition.Succession.html)

```py
from manim import *

class AnimSuccessionExample(Scene):
    def construct(self):
        dots = VGroup(Dot(LEFT), Dot(), Dot(RIGHT))
        self.play(Succession(*[FadeIn(dot) for dot in dots], lag_ratio=0.2))
```
