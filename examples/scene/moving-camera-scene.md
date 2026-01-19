# `scene/moving-camera-scene`

Animate camera frame via `MovingCameraScene`.

Docs: [moving_camera_scene](https://docs.manim.community/en/stable/reference/manim.scene.moving_camera_scene.html)

```py
from manim import *

class MovingCameraSceneExample(MovingCameraScene):
    def construct(self):
        square = Square().shift(LEFT * 2)
        self.add(square)
        self.play(self.camera.frame.animate.move_to(square).scale(0.7))
```
