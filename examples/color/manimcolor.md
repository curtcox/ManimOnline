# `color/manimcolor`

Work with Manim’s canonical color representation.

Docs: [color.core](https://docs.manim.community/en/stable/reference/manim.utils.color.core.html)

```py
from manim import *

class ManimColorExample(Scene):
    def construct(self):
        custom = ManimColor("#00FFAA")
        self.add(Square(fill_color=custom, fill_opacity=1))
```
