"""Render separate ring contours, trace them and change ring dimensions."""
from manim import *


class AnnulusScene(Scene):
    def construct(self):
        ring = Annulus(inner_radius=.7, outer_radius=1.5, color=BLUE,
                       stroke_width=3).save_state()
        self.play(Create(ring), run_time=2)
        dot = Dot(color=YELLOW).move_to(ring.get_start())
        self.add(dot)
        self.play(MoveAlongPath(dot, ring), run_time=4, rate_func=linear)
        self.play(FadeOut(dot), Transform(ring, Annulus(inner_radius=1.2,
                  outer_radius=2, color=GREEN, stroke_width=3)), run_time=2)
        self.play(Restore(ring), run_time=2)
        self.wait(1)
