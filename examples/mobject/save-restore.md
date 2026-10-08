# `mobject/save-restore`

Save state and restore with animations.

Docs: [transform module](https://docs.manim.community/en/stable/reference/manim.animation.transform.html)

```py
from manim import *

class SaveRestoreExample(Scene):
    def construct(self):
        square = Square()
        square.save_state()
        self.play(square.animate.shift(RIGHT).scale(0.5))
        self.play(Restore(square))
```
