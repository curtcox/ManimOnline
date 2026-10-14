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
        self.play(FadeIn(tilted), FadeIn(family), run_time=2, rate_func=linear)
        self.wait(2)
        self.play(FadeOut(tilted), FadeOut(family), run_time=2, rate_func=linear)
        self.wait(2)
