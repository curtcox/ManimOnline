# `coord/axes`

Build 2D axes with ticks and labels.

Docs: [Axes](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.coordinate_systems.Axes.html)

```py
from manim import *

class AxesExample(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-2, 2])
        self.add(axes)
```
