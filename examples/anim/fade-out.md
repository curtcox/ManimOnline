# `anim/fade-out`

Fade out with optional shift/scale.

Docs: [fading](https://docs.manim.community/en/stable/reference/manim.animation.fading.html)

```py
from manim import *

class AnimFadeOutExample(Scene):
    def construct(self):
        shape = Square()
        self.play(FadeOut(shape))
```
