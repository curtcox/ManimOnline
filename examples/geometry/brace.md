# `geometry/brace`

Add braces to annotate lengths/expressions.

Docs: [Brace](https://docs.manim.community/en/stable/reference/manim.mobject.svg.brace.Brace.html)

```py
from manim import *

class GeometryBraceExample(Scene):
    def construct(self):
        line = Line(LEFT, RIGHT)
        brace = Brace(line, direction=DOWN)
        label = brace.get_text("Length")
        self.add(line, brace, label)
```
