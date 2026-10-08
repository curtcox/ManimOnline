from manim import *


class MathScene(Scene):
    def construct(self):
        title = Text("Math rendered as vector paths", font_size=30).shift(UP * 3)
        formula = MathTex(r"\int_0^1 x^2\,dx = \frac{1}{3}", color=BLUE).shift(UP)
        identity = MathTex(r"a^2 + b^2 = c^2", color=GREEN).shift(DOWN)
        self.add(title)
        self.play(Write(formula), Create(identity), run_time=2)
        self.play(Indicate(formula), run_time=2)
        target = MathTex(r"\sum_{k=1}^n k = \frac{n(n+1)}{2}", color=ORANGE).shift(UP)
        self.play(Transform(formula, target), run_time=2)
        self.wait(1)
