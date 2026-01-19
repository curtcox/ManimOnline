# `data/table`

Display tables with row/column labeling.

Docs: [Table](https://docs.manim.community/en/stable/reference/manim.mobject.table.Table.html)

```py
from manim import *

class TableExample(Scene):
    def construct(self):
        table = Table([["A", "B"], ["1", "2"]], row_labels=[Text("R1"), Text("R2")])
        self.add(table)
```
