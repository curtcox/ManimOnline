# `anim/transform-matching-tex`

Match LaTeX substrings during transformations.

Docs: [TransformMatchingTex](https://docs.manim.community/en/stable/reference/manim.animation.transform_matching_parts.TransformMatchingTex.html)

```py
from manim import *

class AnimTransformMatchingTexExample(Scene):
    def construct(self):
        tex1 = MathTex("a^2 + b^2")
        tex2 = MathTex("c^2")
        self.play(TransformMatchingTex(tex1, tex2))
```
