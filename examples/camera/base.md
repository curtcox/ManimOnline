# `camera/base`

Configure frame size, background, pixel dimensions.

Docs: [Camera](https://docs.manim.community/en/stable/reference/manim.camera.camera.Camera.html)

```py
from manim import *

class CameraBaseExample(Scene):
    def construct(self):
        self.camera.background_color = "#1e1e1e"
        self.add(Text("Custom camera"))
```
