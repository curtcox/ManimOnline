"""Follow rounded corners, morph concave cuts, and restore the original outline."""
from manim import *


class RoundedRectangleScene(Scene):
    def construct(self):
        box = RoundedRectangle(width=5, height=3, corner_radius=.6,
                               color=BLUE, fill_opacity=.25).save_state()
        self.play(Create(box), run_time=2)
        dot = Dot(color=YELLOW).move_to(box.get_start())
        self.add(dot)
        self.play(MoveAlongPath(dot, box), run_time=4, rate_func=linear)
        target = RoundedRectangle(width=5, height=3,
                                  corner_radius=[-.8, .2, -.8, .2],
                                  color=GREEN, fill_opacity=.4)
        self.play(FadeOut(dot), Transform(box, target), run_time=2)
        self.play(Restore(box), run_time=2)
        self.wait(1)
