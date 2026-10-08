# `geometry/regular-polygon`

Draw regular n-gons quickly.

Docs: [geometry](https://docs.manim.community/en/stable/reference/manim.mobject.geometry.html)

```py
from manim import *

class GeometryRegularPolygonExample(Scene):
    def construct(self):
        shape = RegularPolygon(n=5)
        self.add(shape)
```
