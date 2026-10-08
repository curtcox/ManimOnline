# `latex/tex`

Render LaTeX strings into vector mobjects.

Docs: [Tex](https://docs.manim.community/en/stable/reference/manim.mobject.text.tex_mobject.Tex.html)

```py
from manim import *

class TexExample(Scene):
    def construct(self):
        self.add(Tex(r"\LaTeX{} text"))
```
