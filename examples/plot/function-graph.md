# `plot/function-graph`

Plot y=f(x) graphs on axes.

Docs: [functions](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.functions.html)

```py
from manim import *

class FunctionGraphExample(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-2, 4])
        graph = axes.plot(lambda x: x**2, color=BLUE)
        self.add(axes, graph)
```
