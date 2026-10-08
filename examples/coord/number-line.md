# `coord/number-line`

Make a labeled number line with ticks.

Docs: [NumberLine](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.number_line.NumberLine.html)

```py
from manim import *

class NumberLineExample(Scene):
    def construct(self):
        line = NumberLine(x_range=[-5, 5, 1])
        self.add(line)
```
