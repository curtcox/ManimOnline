# `scene/foreground`

Keep mobjects on top using foreground list.

Docs: [Scene](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html?highlight=add_sound)

```py
from manim import *

class ForegroundExample(Scene):
    def construct(self):
        background = Square(fill_color=BLUE, fill_opacity=1).scale(3)
        foreground = Text("On Top")
        self.add(background)
        self.add_foreground_mobjects(foreground)
        self.play(foreground.animate.shift(UP))
```
