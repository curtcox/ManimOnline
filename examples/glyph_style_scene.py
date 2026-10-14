from manim import *


class GlyphStyles(Scene):
    def construct(self):
        title = Text("Gradient styles", font_size=48).shift(1.6 * UP)
        formula = MathTex(r"x^2+y^2=1", font_size=64).shift(.3 * DOWN)
        number = DecimalNumber(12.5, font_size=48).shift(1.8 * DOWN)
        labels = VGroup(title, formula, number)
        labels.set_fill([BLUE, GREEN], opacity=[.35, 1])
        labels.set_stroke(WHITE, width=.7, opacity=[.3, .8])
        labels.set_background_stroke([PURPLE, WHITE], width=8, opacity=[.2, .7])
        labels.set_sheen_direction(UP)
        self.play(Write(title), Write(formula), Write(number), run_time=2)
        self.play(
            labels.animate.set_fill([RED, YELLOW], opacity=[1, .4])
            .set_background_stroke([BLUE, GREEN], width=12, opacity=[.8, .3]),
            run_time=2,
            rate_func=linear,
        )
        self.wait(1)
        self.play(FadeOut(labels), run_time=1)
        self.wait(2)
