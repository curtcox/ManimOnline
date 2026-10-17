from manim import *


class Annotations(Scene):
    def construct(self):
        title = Title("Completing the square")
        formula = MathTex("f(x)", "=", "x^2", "+", "2x", "+", "1", font_size=72)
        self.play(Write(title))
        self.play(Write(formula))
        brace = Brace(formula[2:], DOWN)
        label = brace.get_text("a perfect square")
        self.play(GrowFromCenter(brace), FadeIn(label, shift=UP))
        self.wait()
        target = MathTex("f(x)", "=", "(x+1)^2", font_size=72)
        self.play(FadeOut(brace, label))
        self.play(TransformMatchingTex(formula, target))
        self.wait()
