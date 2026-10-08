# `plot/parametric-function`

Plot parametric curves x(t),y(t),z(t).

Docs: [ParametricFunction](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.functions.ParametricFunction.html)

```py
from manim import *

class ParametricFunctionExample(Scene):
    def construct(self):
        curve = ParametricFunction(lambda t: np.array([np.cos(t), np.sin(t), 0]), t_range=[0, TAU])
        self.add(curve)
```
