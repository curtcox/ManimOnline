# `anim/restore`

Animate returning to a saved state.

Docs: [transform module](https://docs.manim.community/en/stable/reference/manim.animation.transform.html)

```py
from manim import *

class AnimRestoreExample(Scene):
    def construct(self):
        square = Square()
        square.save_state()
        self.play(square.animate.shift(RIGHT))
        self.play(Restore(square))
```
