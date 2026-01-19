# `jupyter/magic`

Render scenes inline using Jupyter integration.

Docs: [Jupyter](https://docs.manim.community/en/stable/installation/jupyter.html)

```python
%%manim -ql InlineScene
from manim import *

class InlineScene(Scene):
    def construct(self):
        self.add(Text("Inline render"))
```
