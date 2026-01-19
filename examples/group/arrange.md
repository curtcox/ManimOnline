# `group/arrange`

Arrange objects in a line with spacing.

Docs: [VGroup](https://docs.manim.community/en/stable/reference/manim.mobject.types.vectorized_mobject.VGroup.html)

```py
from manim import *

class ArrangeExample(Scene):
    def construct(self):
        shapes = VGroup(Square(), Circle(), Triangle()).arrange(RIGHT, buff=0.8)
        self.add(shapes)
```
