# `geometry/polygon`

Draw arbitrary polygons from vertices.

Docs: [geometry](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.html)

```py
from manim import *

class GeometryPolygonExample(Scene):
    def construct(self):
        shape = Polygon([-1, 0, 0], [0, 1, 0], [1, 0, 0])
        self.add(shape)
```
