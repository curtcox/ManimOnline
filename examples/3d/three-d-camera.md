# `3d/three-d-camera`

Fix mobjects in frame or orientation in 3D.

Docs: [ThreeDCamera](https://docs.manim.community/en/stable/reference/manim.camera.three_d_camera.ThreeDCamera.html)

```py
from manim import *

class ThreeDCameraExample(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=45 * DEGREES)
        self.add(Text("3D Camera").rotate(PI / 2, axis=RIGHT))
```
