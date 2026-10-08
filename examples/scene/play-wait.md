# `scene/play-wait`

Sequence animations with `play()` and pauses with `wait()`.

Docs: [Scene](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html)

```py
from manim import *

class PlayWaitExample(Scene):
    def construct(self):
        square = Square()
        self.play(Create(square))
        self.wait(0.5)
        self.play(square.animate.shift(RIGHT))
```
