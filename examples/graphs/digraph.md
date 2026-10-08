# `graphs/digraph`

Build directed graphs with arrowed edges.

Docs: [graph module](https://docs.manim.community/en/stable/reference/manim.mobject.graph.html)

```py
from manim import *

class DiGraphExample(Scene):
    def construct(self):
        digraph = DiGraph(vertices=[1, 2, 3], edges=[(1, 2), (2, 3)])
        self.add(digraph)
```
