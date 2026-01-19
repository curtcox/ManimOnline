# `plot/labels`

Add curve labels and axis labels.

Docs: [Axes](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.coordinate_systems.Axes.html)

```py
from manim import *

class PlotLabelsExample(Scene):
    def construct(self):
        axes = Axes(x_range=[-2, 2], y_range=[-1, 3])
        labels = axes.get_axis_labels(x_label="x", y_label="f(x)")
        graph = axes.plot(lambda x: x + 1)
        self.add(axes, graph, labels)
```
