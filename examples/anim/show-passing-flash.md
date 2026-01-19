# `anim/show-passing-flash`

Show only a moving sliver of a stroke.

Docs: [indication](https://docs.manim.community/en/stable/reference/manim.animation.indication.html)

```py
from manim import *

class AnimShowPassingFlashExample(Scene):
    def construct(self):
        shape = Square()
        self.play(ShowPassingFlash(shape))
```
