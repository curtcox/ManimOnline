# `color/gradients`

Generate color gradients for styling.

Docs: [color.core](https://docs.manim.community/en/stable/reference/manim.utils.color.core.html)

```py
from manim import *

class GradientExample(Scene):
    def construct(self):
        colors = color_gradient([BLUE, GREEN, YELLOW], 5)
        dots = VGroup(*[Dot(color=c) for c in colors]).arrange(RIGHT, buff=0.5)
        self.add(dots)
```
