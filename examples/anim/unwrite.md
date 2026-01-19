# `anim/unwrite`

Simulate erasing text or a path.

Docs: [creation](https://docs.manim.community/en/stable/reference/manim.animation.creation.html)

```py
from manim import *

class AnimUnwriteExample(Scene):
    def construct(self):
        shape = Square()
        self.play(Unwrite(shape))
```
