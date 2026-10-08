"""Trace a rotated ellipse, follow its outline and morph to a circle."""
from manim import *


class EllipseScene(Scene):
    def construct(self):
        ellipse = Ellipse(width=4, height=2, color=BLUE).rotate(PI / 6)
        ellipse.save_state()
        dot = Dot(color=YELLOW).move_to(ellipse.point_from_proportion(0))
        self.play(Create(ellipse), run_time=1)
        self.add(dot)
        self.play(MoveAlongPath(dot, ellipse), run_time=4, rate_func=linear)
        self.play(FadeOut(dot), Transform(ellipse, Circle(radius=1.5, color=GREEN)), run_time=2)
        self.play(Restore(ellipse), run_time=2)
        self.wait(1)
