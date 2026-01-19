# `mobject/base`

Understand the core `Mobject` API surface.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class MobjectBaseExample(Scene):
    def construct(self):
        shape = Square().set_color(BLUE)
        self.add(shape)
```
