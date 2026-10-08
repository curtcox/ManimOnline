# `graphs/layouts`

Apply common layouts (spring, circular, etc.).

Docs: [graph module](https://docs.manim.community/en/stable/reference/manim.mobject.graph.html)

```py
from manim import *

class GraphLayoutExample(Scene):
    def construct(self):
        graph = Graph(vertices=[1, 2, 3, 4], edges=[(1, 2), (2, 3), (3, 4)], layout="circular")
        self.add(graph)
```
