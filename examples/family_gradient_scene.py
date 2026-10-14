from manim import *


class FamilyGradientScene(Scene):
    def construct(self):
        tilted = Rectangle(width=4, height=2, fill_color=[RED, BLUE],
                           fill_opacity=1, stroke_width=0)
        tilted.rotate(PI / 4).scale(.7).shift(3 * LEFT)
        family = Square(side_length=2, fill_color=[BLUE, YELLOW],
                        fill_opacity=[.3, 1], stroke_width=0)
        marker = Dot(2 * RIGHT, color=WHITE)
        family.add(marker)
        family.set_stroke([WHITE, GREEN], width=12, opacity=[.2, 1],
                          background=True, family=False)
        family.shift(2 * RIGHT)
        child = Rectangle(width=2, height=1, fill_color=[GREEN, PURPLE],
                          fill_opacity=1, stroke_width=0)
        nested = Square(side_length=1.2, stroke_width=2).add(child)
        nested.rotate(PI / 4).shift(2.5 * UP)
        self.play(FadeIn(tilted), FadeIn(family), FadeIn(nested), run_time=2, rate_func=linear)
        self.wait(2)
        self.play(FadeOut(tilted), FadeOut(family), FadeOut(nested), run_time=2, rate_func=linear)
        self.wait(2)
