from manim import *


class LettersAndParts(Scene):
    def construct(self):
        word = Text("MANIM", font_size=120).shift(UP * 1.5)
        self.play(Write(word))
        self.play(word[0].animate.set_color(YELLOW), word[-1].animate.set_color(YELLOW))
        self.play(LaggedStart(*[letter.animate(rate_func=there_and_back).shift(UP * 0.5) for letter in word],
                              lag_ratio=0.15, run_time=2))

        # Separate strings become separate parts you can index.
        formula = MathTex("a^2", "+", "b^2", "=", "c^2", font_size=96).shift(DOWN * 1.5)
        self.play(Write(formula))
        self.play(formula[0].animate.set_color(BLUE), formula[2].animate.set_color(GREEN),
                  formula[4].animate.set_color(RED))
        self.wait()
