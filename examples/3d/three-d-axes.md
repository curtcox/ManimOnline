# `3d/three-d-axes`

Use 3D axes for spatial plots.

Docs: [ThreeDAxes](https://docs.manim.community/en/stable/reference/manim.mobject.graphing.coordinate_systems.ThreeDAxes.html)

```py
from manim import *

class ThreeDAxesExample(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        self.add(axes)
        self.set_camera_orientation(phi=70 * DEGREES, theta=30 * DEGREES)
```
