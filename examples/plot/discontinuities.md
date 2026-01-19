# `plot/discontinuities`

Plot functions with specified discontinuities.

Docs: [ParametricFunction](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.functions.ParametricFunction.html)

```py
from manim import *

class DiscontinuityExample(Scene):
    def construct(self):
        axes = Axes(x_range=[-4, 4], y_range=[-4, 4])
        graph = axes.plot(lambda x: 1 / x, x_range=[-4, 4], discontinuities=[0])
        self.add(axes, graph)
```
