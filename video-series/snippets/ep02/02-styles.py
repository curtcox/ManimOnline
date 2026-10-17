from manim import *


class Styles(Scene):
    def construct(self):
        shapes = VGroup(
            Circle().set_stroke(BLUE, width=8),                                  # outline only
            Square().set_fill(GREEN, opacity=1).set_stroke(width=0),             # fill only
            Triangle().set_fill(RED, opacity=0.4).set_stroke(YELLOW, width=4),   # both
            RegularPolygon(6).set_fill(PURPLE, opacity=0.7).set_stroke(WHITE, width=2),
        ).arrange(RIGHT, buff=0.6)
        self.play(LaggedStart(*[Create(s) for s in shapes], lag_ratio=0.3))
        self.play(shapes[0].animate.set_fill(BLUE, opacity=0.5))
        self.play(shapes[1].animate.set_color("#FF8800"))
        self.wait()
