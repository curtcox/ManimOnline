# `mobject/position-shift`

Translate a mobject by a vector.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class ShiftExample(Scene):
    def construct(self):
        square = Square()
        square.shift(RIGHT * 2)
        self.add(square)
```
