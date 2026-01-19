# `data/matrix`

Render matrices with bracket styling and entries.

Docs: [Matrix](https://docs.manim.community/en/stable/reference/manim.mobject.matrix.Matrix.html)

```py
from manim import *

class MatrixExample(Scene):
    def construct(self):
        matrix = Matrix([[1, 2], [3, 4]])
        self.add(matrix)
```
