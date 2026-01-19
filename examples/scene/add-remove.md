# `scene/add-remove`

Add/remove mobjects from a scene.

Docs: [Scene](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html)

```py
from manim import *

class AddRemoveExample(Scene):
    def construct(self):
        dot = Dot()
        self.add(dot)
        self.wait(0.5)
        self.remove(dot)
```
