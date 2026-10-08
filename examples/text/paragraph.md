# `text/paragraph`

Wrap text into multi-line paragraph objects.

Docs: [Using text](https://docs.manim.community/en/stable/guides/using_text.html)

```py
from manim import *

class ParagraphExample(Scene):
    def construct(self):
        para = Paragraph("Line one", "Line two", alignment="center")
        self.add(para)
```
