# `data/math-table`

Use LaTeX-rendered cells for tables.

Docs: [table module](https://docs.manim.community/en/stable/reference/manim.mobject.table.html)

```py
from manim import *

class MathTableExample(Scene):
    def construct(self):
        table = MathTable([["a", "b"], ["c", "d"]])
        self.add(table)
```
