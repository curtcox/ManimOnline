# `latex/tex-template`

Customize LaTeX preamble, packages, and fonts.

Docs: [TexTemplate](https://docs.manim.community/en/stable/reference/manim.utils.tex.TexTemplate.html)

```py
from manim import *

class TexTemplateExample(Scene):
    def construct(self):
        template = TexTemplate()
        template.add_to_preamble(r"\usepackage{amsmath}")
        self.add(Tex(r"\text{Custom preamble}", tex_template=template))
```
