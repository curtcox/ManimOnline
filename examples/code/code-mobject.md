# `code/code-mobject`

Display syntax-highlighted code blocks.

Docs: [Code](https://docs.manim.community/en/stable/reference/manim.mobject.text.code_mobject.Code.html)

```py
from manim import *

class CodeMobjectExample(Scene):
    def construct(self):
        code = Code(code="print("Hello")", language="python", tab_width=4)
        self.add(code)
```
