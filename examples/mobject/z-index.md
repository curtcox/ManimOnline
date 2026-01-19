# `mobject/z-index`

Control draw order with z-index sorting.

Docs: [Camera](https://docs.manim.community/en/stable/reference/manim.camera.camera.Camera.html)

```py
from manim import *

class ZIndexExample(Scene):
    def construct(self):
        back = Square(fill_color=BLUE, fill_opacity=1).scale(2)
        front = Circle(fill_color=YELLOW, fill_opacity=1).set_z_index(1)
        self.add(back, front)
```
