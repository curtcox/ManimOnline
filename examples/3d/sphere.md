# `3d/sphere`

Render a sphere surface in 3D.

Docs: [Sphere](https://docs.manim.community/en/stable/reference/manim.mobject.three_d.three_dimensions.Sphere.html)

```py
from manim import *

class SphereExample(ThreeDScene):
    def construct(self):
        sphere = Sphere(radius=1, resolution=(12, 24))
        self.add(sphere)
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
```
