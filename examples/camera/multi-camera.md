# `camera/multi-camera`

Render multiple camera views in one frame.

Docs: [MultiCamera](https://docs.manim.community/en/stable/reference/manim.camera.multi_camera.MultiCamera.html)

```py
from manim import *

class MultiCameraExample(Scene):
    def __init__(self, **kwargs):
        super().__init__(camera=MultiCamera(number_of_cameras=2), **kwargs)

    def construct(self):
        self.add(Text("Multi-camera"))
```
