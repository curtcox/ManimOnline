# `camera/moving-camera`

Follow a frame rectangle that can animate.

Docs: [MovingCamera](https://docs.manim.community/en/stable/reference/manim.camera.moving_camera.MovingCamera.html)

```py
from manim import *

class MovingCameraExample(MovingCameraScene):
    def construct(self):
        dot = Dot().shift(RIGHT * 2)
        self.add(dot)
        self.play(self.camera.frame.animate.move_to(dot).scale(0.5))
```
