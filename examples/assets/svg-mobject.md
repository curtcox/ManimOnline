# `assets/svg-mobject`

Import and manipulate SVG vector artwork.

Docs: [SVGMobject](https://docs.manim.community/en/stable/reference/manim.mobject.svg.svg_mobject.SVGMobject.html)

```py
from manim import *

class SvgMobjectExample(Scene):
    def construct(self):
        icon = SVGMobject("example.svg")
        self.add(icon)
```
