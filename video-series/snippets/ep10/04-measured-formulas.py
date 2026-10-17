from manim import *


class MeasuredFormulas(Scene):
    def construct(self):
        formulas = VGroup(
            MathTex(r"\int_0^1 x^2 \, dx = \frac{1}{3}"),
            MathTex(r"\sqrt{\frac{a^2 + b^2}{2}}"),
            MathTex(r"\sum_{k=0}^{n} \binom{n}{k} = 2^n"),
        ).arrange(DOWN, buff=0.8)
        boxes = VGroup(*[SurroundingRectangle(f, buff=0.05, color=YELLOW) for f in formulas])
        self.play(LaggedStart(*[Write(f) for f in formulas], lag_ratio=0.4))
        self.play(Create(boxes))   # tight boxes need measured glyphs, not guesses
        self.wait()
