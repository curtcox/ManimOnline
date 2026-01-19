# `anim/fade-in`

Fade in with optional shift/scale.

Docs: [fading](https://docs.manim.community/en/stable/reference/manim.animation.fading.html)

```py
from manim import *

class AnimFadeInExample(Scene):
    def construct(self):
        shape = Square()
        self.play(FadeIn(shape))
```
