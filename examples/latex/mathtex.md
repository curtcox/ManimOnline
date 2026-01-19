# `latex/mathtex`

Render LaTeX math into vector mobjects.

Docs: [Tex](https://docs.manim.community/en/stable/reference/manim.mobject.text.tex_mobject.Tex.html)

```py
from manim import *

class MathTexExample(Scene):
    def construct(self):
        self.add(MathTex(r"\int_0^1 x^2 \, dx"))
```
