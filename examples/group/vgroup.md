# `group/vgroup`

Group mobjects for collective transforms.

Docs: [VGroup](https://docs.manim.community/en/stable/reference/manim.mobject.types.vectorized_mobject.VGroup.html)

```py
from manim import *

class VGroupExample(Scene):
    def construct(self):
        dots = VGroup(*[Dot() for _ in range(3)]).arrange(RIGHT, buff=0.5)
        self.add(dots)
```
