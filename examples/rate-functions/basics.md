# `rate-functions/basics`

Change easing with `rate_func`.

Docs: [rate_functions](https://docs.manim.community/en/stable/reference/manim.utils.rate_functions.html)

```py
from manim import *

class RateFunctionExample(Scene):
    def construct(self):
        square = Square()
        self.add(square)
        self.play(square.animate.shift(RIGHT * 2), rate_func=rate_functions.ease_in_out_sine)
```
