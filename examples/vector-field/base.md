# `vector-field/base`

Define a vector field from a function.

Docs: [vector_field](https://docs.manim.community/en/stable/reference/manim.mobject.vector_field.html)

```py
from manim import *

class VectorFieldBaseExample(Scene):
    def construct(self):
        field = VectorField(lambda p: np.array([p[1], -p[0], 0]))
        self.add(field)
```
