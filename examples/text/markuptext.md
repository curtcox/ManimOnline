# `text/markuptext`

Use lightweight markup for rich text styling.

Docs: [Using text](https://docs.manim.community/en/stable/guides/using_text.html)

```py
from manim import *

class MarkupTextExample(Scene):
    def construct(self):
        self.add(MarkupText("<b>Bold</b> and <span fgcolor="#FF00FF">color</span>"))
```
