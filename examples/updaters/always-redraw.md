# `updaters/always-redraw`

Recompute a mobject each frame from a lambda.

Docs: [always_redraw](https://docs.manim.community/en/stable/reference/manim.mobject.mobject_update_utils.always_redraw.html)

```py
from manim import *

class AlwaysRedrawExample(Scene):
    def construct(self):
        tracker = ValueTracker(0)
        dot = always_redraw(lambda: Dot().move_to(RIGHT * tracker.get_value()))
        self.add(dot)
        self.play(tracker.animate.set_value(3))
```
