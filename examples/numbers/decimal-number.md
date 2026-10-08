# `numbers/decimal-number`

Display and animate numeric readouts.

Docs: [DecimalNumber](https://docs.manim.community/en/stable/reference/manim.mobject.text.numbers.DecimalNumber.html)

```py
from manim import *

class DecimalNumberExample(Scene):
    def construct(self):
        number = DecimalNumber(3.14, num_decimal_places=2)
        self.add(number)
```
