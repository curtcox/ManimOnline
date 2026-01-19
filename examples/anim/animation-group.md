# `anim/animation-group`

Play multiple animations concurrently.

Docs: [composition](https://docs.manim.community/en/stable/reference/manim.animation.composition.html)

```py
from manim import *

class AnimAnimationGroupExample(Scene):
    def construct(self):
        dots = VGroup(Dot(LEFT), Dot(), Dot(RIGHT))
        self.play(AnimationGroup(*[FadeIn(dot) for dot in dots], lag_ratio=0.2))
```
