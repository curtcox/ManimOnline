# `mobject/style-fill-stroke`

Set fill/stroke color, opacity, and width.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class FillStrokeExample(Scene):
    def construct(self):
        square = Square()
        square.set_fill(BLUE, opacity=0.6)
        square.set_stroke(YELLOW, width=6)
        self.add(square)
```
