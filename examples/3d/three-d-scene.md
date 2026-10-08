# `3d/three-d-scene`

Enable 3D camera controls and ambient rotation.

Docs: [three_d_scene](https://docs.manim.community/en/stable/reference/manim.scene.three_d_scene.html)

```py
from manim import *

class ThreeDSceneExample(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        self.add(axes)
        self.set_camera_orientation(phi=75 * DEGREES, theta=45 * DEGREES)
```
