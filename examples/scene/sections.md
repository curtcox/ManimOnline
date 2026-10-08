# `scene/sections`

Segment videos using section markers.

Docs: [Scene](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html)

```py
from manim import *

class SectionsExample(Scene):
    def construct(self):
        self.next_section("intro")
        self.play(Write(Text("Section 1")))
        self.next_section("outro")
        self.play(Write(Text("Section 2")))
```
