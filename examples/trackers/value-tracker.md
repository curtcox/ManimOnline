# `trackers/value-tracker`

Animate scalar parameters without displaying them.

Docs: [ValueTracker](https://docs.manim.community/en/stable/reference/manim.mobject.value_tracker.ValueTracker.html)

```py
from manim import *

class ValueTrackerExample(Scene):
    def construct(self):
        tracker = ValueTracker(0)
        number = DecimalNumber().add_updater(lambda m: m.set_value(tracker.get_value()))
        self.add(number)
        self.play(tracker.animate.set_value(5))
        number.clear_updaters()
```
