# `graphs/graph`

Build combinatorial graphs with vertices and edges.

Docs: [Graph](https://docs.manim.community/en/stable/reference/manim.mobject.graph.Graph.html)

```py
from manim import *

class GraphExample(Scene):
    def construct(self):
        graph = Graph(vertices=[1, 2, 3], edges=[(1, 2), (2, 3)])
        self.add(graph)
```
