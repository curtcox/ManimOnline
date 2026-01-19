# `anim/lagged-start`

Stagger sub-animations using lag ratio.

Docs: [composition](https://docs.manim.community/en/stable/reference/manim.animation.composition.html)

```py
from manim import *

class AnimLaggedStartExample(Scene):
    def construct(self):
        dots = VGroup(Dot(LEFT), Dot(), Dot(RIGHT))
        self.play(LaggedStart(*[FadeIn(dot) for dot in dots], lag_ratio=0.2))
```
