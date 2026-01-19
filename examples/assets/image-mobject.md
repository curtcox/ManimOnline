# `assets/image-mobject`

Import raster images (PNG/JPG) as mobjects.

Docs: [ImageMobject](https://docs.manim.community/en/stable/reference/manim.mobject.types.image_mobject.ImageMobject.html)

```py
from manim import *

class ImageMobjectExample(Scene):
    def construct(self):
        image = ImageMobject("example.png").scale(0.5)
        self.add(image)
```
