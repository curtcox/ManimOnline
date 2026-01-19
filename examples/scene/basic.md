# `scene/basic`

Minimal `Scene` with `construct()` method.

Docs: [Scene](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html)

```py
from manim import *

class BasicSceneExample(Scene):
    def construct(self):
        title = Text("Basic Scene")
        self.add(title)
```
