# `vector-field/arrows`

Show vector fields as arrow glyphs.

Docs: [vector_field](https://docs.manim.community/en/stable/reference/manim.mobject.vector_field.html)

```py
from manim import *

class VectorFieldArrowsExample(Scene):
    def construct(self):
        field = ArrowVectorField(lambda p: np.array([p[1], -p[0], 0]))
        self.add(field)
```
