# `3d/surface`

Render parametric surfaces with UV sampling.

Docs: [Surface](https://docs.manim.community/en/stable/reference/manim.mobject.three_d.three_dimensions.Surface.html)

```py
from manim import *

class SurfaceExample(ThreeDScene):
    def construct(self):
        surface = Surface(lambda u, v: np.array([u, v, u * v / 2]), u_range=[-1, 1], v_range=[-1, 1])
        self.add(surface)
        self.set_camera_orientation(phi=70 * DEGREES, theta=30 * DEGREES)
```
