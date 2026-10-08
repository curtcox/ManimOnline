# `scene/zoomed-scene`

Create inset magnified views with zoom window.

Docs: [ZoomedScene](https://docs.manim.community/en/stable/reference/manim.scene.zoomed_scene.ZoomedScene.html)

```py
from manim import *

class ZoomedSceneExample(ZoomedScene):
    def construct(self):
        dot = Dot().shift(RIGHT * 2)
        self.add(dot)
        self.activate_zooming()
        self.play(self.zoomed_camera.frame.animate.move_to(dot))
```
