# `anim/circumscribe`

Draw a temporary outline around an object.

Docs: [indication](https://docs.manim.community/en/stable/reference/manim.animation.indication.html)

```py
from manim import *

class AnimCircumscribeExample(Scene):
    def construct(self):
        shape = Square()
        self.play(Circumscribe(shape))
```
