# `updaters/add-updater`

Attach a function executed every frame.

Docs: [Mobject](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html)

```py
from manim import *

class AddUpdaterExample(Scene):
    def construct(self):
        dot = Dot()
        label = always_redraw(lambda: Text(f"x={dot.get_center()[0]:.1f}").next_to(dot, UP))
        dot.add_updater(lambda m, dt: m.shift(RIGHT * dt))
        self.add(dot, label)
        self.wait(1)
        dot.clear_updaters()
```
