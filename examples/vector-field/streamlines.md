# `vector-field/streamlines`

Visualize flow using moving streamline tracers.

Docs: [vector_field](https://docs.manim.community/en/stable/reference/manim.mobject.vector_field.html)

```py
from manim import *

class VectorFieldStreamlinesExample(Scene):
    def construct(self):
        field = VectorField(lambda p: np.array([p[1], -p[0], 0]))
        streamlines = StreamLines(field.func, virtual_time=2)
        self.add(streamlines)
        streamlines.start_animation()
        self.wait(1)
```
